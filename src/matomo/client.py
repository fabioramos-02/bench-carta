"""Cliente HTTP da API Reporting do Matomo.

Responsabilidade única: transporte. Monta a requisição, autentica via
`token_auth`, devolve JSON. Não conhece regras de negócio do estudo.
Cache em memória evita repetir a mesma chamada na mesma execução.
"""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Any

import requests

from src.config import MatomoSettings
from src.obs import log_api_call, setup_logging

logger = logging.getLogger(__name__)

_TIMEOUT = 180  # s — período 'year' é pesado no servidor do portal


class MatomoClient:
    """Wrapper fino sobre a Reporting API (formato JSON)."""

    def __init__(self, settings: MatomoSettings, session: requests.Session | None = None):
        self._s = settings
        self._http = session or requests.Session()

    def call(self, method: str, **params: Any) -> Any:
        """Executa um método da Reporting API e devolve o JSON decodificado.

        Cada chamada gera um registro estruturado (src.obs): status HTTP,
        duração, volume e erro. Re-levanta a exceção para o chamador tratar.
        """
        payload = {
            "module": "API",
            "method": method,
            "idSite": self._s.id_site,
            "period": params.pop("period", self._s.period),
            "date": params.pop("date", self._s.date),
            "format": "JSON",
            "token_auth": self._s.token,
            **params,
        }
        redacted = _redact(payload)
        start = time.perf_counter()
        try:
            resp = self._http.post(self._s.api_url, data=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            _raise_if_api_error(data, method)
        except Exception as exc:  # noqa: BLE001 — logar e re-levantar
            log_api_call(
                source="matomo",
                method=method,
                ok=False,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                error=f"{type(exc).__name__}: {exc}",
                period=redacted.get("period"),
                date=redacted.get("date"),
                segment=redacted.get("segment"),
            )
            raise

        kind = "list" if isinstance(data, list) else "dict" if isinstance(data, dict) else "other"
        log_api_call(
            source="matomo",
            method=method,
            ok=True,
            duration_ms=(time.perf_counter() - start) * 1000.0,
            status=resp.status_code,
            n_bytes=len(resp.content),
            kind=kind,
            n_items=(len(data) if isinstance(data, (list, dict)) else None),
            period=redacted.get("period"),
            date=redacted.get("date"),
            segment=redacted.get("segment"),
        )
        return data


def _raise_if_api_error(data: Any, method: str) -> None:
    if isinstance(data, dict) and data.get("result") == "error":
        raise RuntimeError(f"Matomo {method} retornou erro: {data.get('message')}")


def _redact(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: ("***" if k == "token_auth" else v) for k, v in payload.items()}


@lru_cache(maxsize=1)
def get_client() -> MatomoClient:
    """Cliente singleton para reuso de sessão e cache durante a execução."""
    from src.config import load_settings

    setup_logging()
    return MatomoClient(load_settings())
