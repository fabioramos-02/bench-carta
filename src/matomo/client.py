"""Cliente HTTP da API Reporting do Matomo.

Responsabilidade única: transporte. Monta a requisição, autentica via
`token_auth`, devolve JSON. Não conhece regras de negócio do estudo.
Cache em memória evita repetir a mesma chamada na mesma execução.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import requests

from src.config import MatomoSettings

logger = logging.getLogger(__name__)

_TIMEOUT = 180  # s — período 'year' é pesado no servidor do portal


class MatomoClient:
    """Wrapper fino sobre a Reporting API (formato JSON)."""

    def __init__(self, settings: MatomoSettings, session: requests.Session | None = None):
        self._s = settings
        self._http = session or requests.Session()

    def call(self, method: str, **params: Any) -> Any:
        """Executa um método da Reporting API e devolve o JSON decodificado."""
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
        logger.info("Matomo %s params=%s", method, _redact(payload))
        resp = self._http.post(self._s.api_url, data=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        _raise_if_api_error(data, method)
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

    return MatomoClient(load_settings())
