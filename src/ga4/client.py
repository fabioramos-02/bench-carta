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

# Imports do SDK Google são LAZY (dentro dos métodos) para não exigir o pacote
# `google-analytics-data` no boot do app — só ao consultar o GA4 de fato.
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
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2.credentials import Credentials

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
        self, dimensions: list[str], metrics: list[str], start: str, end: str,
        dimension_filter=None,
    ) -> list[dict]:
        """Roda um relatório e devolve linhas como dicts {dim/met: valor}.

        `dimensions` pode ser vazio (consulta só de métrica — ex.: união de
        únicos sob filtro). `dimension_filter` é um FilterExpression opcional do
        SDK; em fallback de dimensão, o field_name dentro do filtro também é
        trocado (ver `_swap_filter_field`).

        Em caso de dimensão inválida, troca pelo fallback e tenta de novo.
        Cada tentativa gera um registro estruturado (src.obs).
        """
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest,
        )

        start_t = time.perf_counter()
        try:
            request = RunReportRequest(
                property=self._property,
                dimensions=[Dimension(name=d) for d in dimensions],
                metrics=[Metric(name=m) for m in metrics],
                date_ranges=[DateRange(start_date=start, end_date=end)],
                dimension_filter=dimension_filter,
                limit=500,
            )
            response = self._client.run_report(request)
        except Exception as exc:  # noqa: BLE001 — fallback dinâmico de dimensão
            # Detecta "Field X is not a valid dimension" — X pode estar nas
            # dimensions OU dentro do dimension_filter (caso da união de únicos).
            match = re.search(r"Field (\w+) is not a valid dimension", str(exc))
            campo = match.group(1) if match else None
            if campo and campo in _DIM_FALLBACK:
                novo_campo = _DIM_FALLBACK[campo]
                novas_dims = [novo_campo if d == campo else d for d in dimensions]
                novo_filtro = self._swap_filter_field(dimension_filter, campo, novo_campo)
                mudou = novas_dims != dimensions or novo_filtro is not dimension_filter
                if mudou:
                    log_api_call(
                        source="ga4", method="runReport", ok=False,
                        duration_ms=(time.perf_counter() - start_t) * 1000.0,
                        event="dim_fallback", dimensions=dimensions, fallback=novas_dims,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    return self.run_report(novas_dims, metrics, start, end, novo_filtro)
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

    def run_reports_batch(
        self, specs: list[dict], start: str, end: str
    ) -> list[list[dict]]:
        """Roda vários relatórios em lotes de 5 (GA4 batchRunReports) e devolve
        a lista de linhas por spec, na MESMA ordem de `specs`.

        Cada spec: {"metrics": [...], "dimensions": [...]?, "dimension_filter": expr?}.
        Troca N round-trips por N/5 — derruba a latência dominante (I/O de rede).
        Se um lote falhar, faz fallback sequencial por spec (com fallback de dimensão).
        """
        from google.analytics.data_v1beta.types import (
            BatchRunReportsRequest, DateRange, Dimension, Metric, RunReportRequest,
        )

        resultados: list[list[dict]] = [[] for _ in specs]
        for ini in range(0, len(specs), 5):
            lote = specs[ini:ini + 5]
            reqs = [
                RunReportRequest(
                    dimensions=[Dimension(name=d) for d in s.get("dimensions", [])],
                    metrics=[Metric(name=m) for m in s["metrics"]],
                    date_ranges=[DateRange(start_date=start, end_date=end)],
                    dimension_filter=s.get("dimension_filter"),
                    limit=500,
                )
                for s in lote
            ]
            start_t = time.perf_counter()
            try:
                resp = self._client.batch_run_reports(
                    BatchRunReportsRequest(property=self._property, requests=reqs)
                )
                for i, rep in enumerate(resp.reports):
                    resultados[ini + i] = self._rows_from(rep, lote[i])
                log_api_call(
                    source="ga4", method="batchRunReports", ok=True,
                    duration_ms=(time.perf_counter() - start_t) * 1000.0,
                    n_reports=len(reqs), date_range=f"{start}..{end}",
                )
            except Exception as exc:  # noqa: BLE001 — fallback sequencial do lote
                log_api_call(
                    source="ga4", method="batchRunReports", ok=False,
                    duration_ms=(time.perf_counter() - start_t) * 1000.0,
                    n_reports=len(reqs), error=f"{type(exc).__name__}: {exc}",
                )
                for i, s in enumerate(lote):
                    resultados[ini + i] = self.run_report(
                        s.get("dimensions", []), s["metrics"], start, end,
                        s.get("dimension_filter"),
                    )
        return resultados

    @staticmethod
    def _rows_from(report, spec: dict) -> list[dict]:
        dims = spec.get("dimensions", [])
        mets = spec["metrics"]
        out: list[dict] = []
        for row in report.rows:
            entry: dict = {}
            for i, d in enumerate(dims):
                entry[d] = row.dimension_values[i].value
            for i, m in enumerate(mets):
                entry[m] = row.metric_values[i].value
            out.append(entry)
        return out

    @staticmethod
    def _swap_filter_field(expr, campo: str | None, novo: str | None):
        """Troca recursivamente `field_name == campo` por `novo` num
        FilterExpression. Devolve o MESMO objeto se nada mudar (identidade usada
        para detectar alteração). Sem `campo`/`expr` → retorna `expr` intacto."""
        if expr is None or not campo:
            return expr
        which = expr.WhichOneof("expr") if hasattr(expr, "WhichOneof") else None
        if which == "filter" and expr.filter.field_name == campo:
            from google.analytics.data_v1beta.types import Filter, FilterExpression
            novo_filter = Filter()
            novo_filter._pb.CopyFrom(expr.filter._pb)
            novo_filter.field_name = novo
            return FilterExpression(filter=novo_filter)
        if which in ("and_group", "or_group"):
            grupo = getattr(expr, which)
            trocou = False
            novas = []
            for sub in grupo.expressions:
                ns = GA4Client._swap_filter_field(sub, campo, novo)
                trocou = trocou or ns is not sub
                novas.append(ns)
            if not trocou:
                return expr
            from google.analytics.data_v1beta.types import (
                FilterExpression, FilterExpressionList,
            )
            lista = FilterExpressionList(expressions=novas)
            return FilterExpression(**{which: lista})
        return expr


@lru_cache(maxsize=1)
def get_ga4_client() -> GA4Client:
    """Cliente singleton para reuso durante a execução."""
    from src.config import load_ga4_settings

    setup_logging()
    return GA4Client(load_ga4_settings())
