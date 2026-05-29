"""Cliente da Data API do Google Analytics 4 (app MS Digital).

Responsabilidade única: transporte + autenticação OAuth (refresh token). Monta
o RunReportRequest, devolve linhas como lista de dicts. Não conhece as regras
de negócio do estudo (ficam em `ga4.queries`).

Inclui fallback de dimensão de tela: se `unifiedScreenName` não existir na
propriedade, tenta `screenName`/`pageTitle` automaticamente.
"""
from __future__ import annotations

import logging
import re
import time
from functools import lru_cache

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2.credentials import Credentials

from src.config import GA4Settings
from src.obs import log_api_call, setup_logging

logger = logging.getLogger(__name__)

# Substituições de campos quando a propriedade não suporta a dimensão pedida.
_DIM_FALLBACK = {
    "unifiedScreenName": "screenName",
    "screenName": "pageTitle",
}


class GA4Client:
    """Wrapper fino sobre BetaAnalyticsDataClient (OAuth via refresh token)."""

    def __init__(self, settings: GA4Settings):
        self._property = f"properties/{settings.property_id}"
        credentials = Credentials(
            token=None,
            refresh_token=settings.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        self._client = BetaAnalyticsDataClient(credentials=credentials)

    def run_report(
        self, dimensions: list[str], metrics: list[str], start: str, end: str
    ) -> list[dict]:
        """Roda um relatório e devolve linhas como dicts {dim/met: valor}.

        Em caso de dimensão inválida, troca pelo fallback e tenta de novo.
        Cada tentativa gera um registro estruturado (src.obs).
        """
        start_t = time.perf_counter()
        try:
            request = RunReportRequest(
                property=self._property,
                dimensions=[Dimension(name=d) for d in dimensions],
                metrics=[Metric(name=m) for m in metrics],
                date_ranges=[DateRange(start_date=start, end_date=end)],
                limit=500,
            )
            response = self._client.run_report(request)
        except Exception as exc:  # noqa: BLE001 — fallback dinâmico de dimensão
            novo = self._with_fallback(dimensions, str(exc))
            if novo is not None:
                log_api_call(
                    source="ga4", method="runReport", ok=False,
                    duration_ms=(time.perf_counter() - start_t) * 1000.0,
                    event="dim_fallback", dimensions=dimensions, fallback=novo,
                    error=f"{type(exc).__name__}: {exc}",
                )
                return self.run_report(novo, metrics, start, end)
            log_api_call(
                source="ga4", method="runReport", ok=False,
                duration_ms=(time.perf_counter() - start_t) * 1000.0,
                dimensions=dimensions, metrics=metrics,
                error=f"{type(exc).__name__}: {exc}",
            )
            return []

        rows: list[dict] = []
        for row in response.rows:
            entry: dict = {}
            for i, dim in enumerate(dimensions):
                entry[dim] = row.dimension_values[i].value
            for i, met in enumerate(metrics):
                entry[met] = row.metric_values[i].value
            rows.append(entry)

        log_api_call(
            source="ga4", method="runReport", ok=True,
            duration_ms=(time.perf_counter() - start_t) * 1000.0,
            dimensions=dimensions, metrics=metrics, n_rows=len(rows),
            date_range=f"{start}..{end}",
        )
        return rows

    @staticmethod
    def _with_fallback(dimensions: list[str], err: str) -> list[str] | None:
        match = re.search(r"Field (\w+) is not a valid dimension", err)
        if not match:
            return None
        field = match.group(1)
        if field not in dimensions or field not in _DIM_FALLBACK:
            return None
        nova = list(dimensions)
        nova[nova.index(field)] = _DIM_FALLBACK[field]
        return nova


@lru_cache(maxsize=1)
def get_ga4_client() -> GA4Client:
    """Cliente singleton para reuso durante a execução."""
    from src.config import load_ga4_settings

    setup_logging()
    return GA4Client(load_ga4_settings())
