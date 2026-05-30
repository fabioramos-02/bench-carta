"""Consultas de domínio sobre o GA4 para a demanda de acessos por categoria.

Responsabilidade única: traduzir "quantas pessoas acessam a categoria X no app
MS Digital" em relatórios da Data API e devolver números limpos. Sem transporte
(fica em `ga4.client`).

"pessoas" = activeUsers (usuários únicos no período).
"acessos" = screenPageViews (visualizações de tela, conta repetição).
"""
from __future__ import annotations

import unicodedata

from src.ga4.client import GA4Client

_SCREEN_DIM = "unifiedScreenName"


def _norm(label: str) -> str:
    """Minúsculas sem acento, para casar rótulos de forma robusta."""
    s = unicodedata.normalize("NFKD", label or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def screens_metrics(client: GA4Client, start: str, end: str) -> dict[str, dict]:
    """Métricas por tela do app (serviços nativos).

    Retorna {norm(rótulo): {"pessoas": activeUsers, "acessos": screenPageViews}}.
    """
    rows = client.run_report(
        [_SCREEN_DIM], ["activeUsers", "screenPageViews"], start, end
    )
    agg: dict[str, dict] = {}
    for r in rows:
        label = next((v for k, v in r.items() if k not in ("activeUsers", "screenPageViews")), "")
        chave = _norm(label)
        a = agg.setdefault(chave, {"pessoas": 0, "acessos": 0})
        a["pessoas"] += int(r.get("activeUsers", 0) or 0)
        a["acessos"] += int(r.get("screenPageViews", 0) or 0)
    return agg


def clicks_metrics(client: GA4Client, start: str, end: str) -> dict[str, dict]:
    """Métricas por clique de redirecionamento (serviços redirect).

    Evento `click` por `linkText`. Filtra eventName==click em Python (run_report
    não suporta filtro de dimensão).
    Retorna {norm(linkText): {"pessoas": totalUsers, "cliques": eventCount}}.
    """
    rows = client.run_report(
        ["eventName", "linkText"], ["eventCount", "totalUsers"], start, end
    )
    agg: dict[str, dict] = {}
    for r in rows:
        if r.get("eventName") != "click":
            continue
        chave = _norm(r.get("linkText", ""))
        if not chave or chave in ("(not set)", "unknown"):
            continue
        a = agg.setdefault(chave, {"pessoas": 0, "cliques": 0})
        a["pessoas"] += int(r.get("totalUsers", 0) or 0)
        a["cliques"] += int(r.get("eventCount", 0) or 0)
    return agg


def build_category_filter(native_labels: list[str], redirect_labels: list[str]):
    """FilterExpression OR p/ a união de únicos da categoria (ou None se vazio).

    OR: (unifiedScreenName inList nativos) OU (eventName==click AND linkText
    inList redirects). Usado em lote (batchRunReports) com a métrica activeUsers.
    """
    from google.analytics.data_v1beta.types import (
        Filter, FilterExpression, FilterExpressionList,
    )

    ramos: list = []
    if native_labels:
        ramos.append(FilterExpression(filter=Filter(
            field_name=_SCREEN_DIM,
            in_list_filter=Filter.InListFilter(values=native_labels, case_sensitive=False),
        )))
    if redirect_labels:
        ramos.append(FilterExpression(and_group=FilterExpressionList(expressions=[
            FilterExpression(filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(value="click"),
            )),
            FilterExpression(filter=Filter(
                field_name="linkText",
                in_list_filter=Filter.InListFilter(values=redirect_labels, case_sensitive=False),
            )),
        ])))
    if not ramos:
        return None
    return ramos[0] if len(ramos) == 1 else FilterExpression(
        or_group=FilterExpressionList(expressions=ramos)
    )


def category_unique_users(
    client: GA4Client,
    native_labels: list[str],
    redirect_labels: list[str],
    start: str,
    end: str,
) -> int:
    """União de usuários ÚNICOS que tocaram QUALQUER serviço da categoria.

    `activeUsers` é user-scoped → mesma pessoa em 2 serviços conta 1× (fica entre
    o maior serviço e a soma). Retorna 0 se sem rótulos/dados. Uso pontual; o
    `compute_app` agora usa `build_category_filter` + `run_reports_batch`."""
    expr = build_category_filter(native_labels, redirect_labels)
    if expr is None:
        return 0
    rows = client.run_report([], ["activeUsers"], start, end, dimension_filter=expr)
    return sum(int(r.get("activeUsers", 0) or 0) for r in rows)


def categoria_acessos(
    client: GA4Client, categorias_map: dict[str, str], start: str, end: str
) -> dict[str, dict]:
    """Pessoas e acessos por categoria, casando rótulo exato da tela.

    Args:
        categorias_map: {categoria_demanda -> rótulo da tela no GA4}.
            Ex.: {"servidor": "Servidor Público", "holerite": "Contracheque"}.

    Retorna:
        {categoria: {"tela": <rótulo>, "pessoas": int, "acessos": int}}.
        Categorias sem dado vêm com zero.
    """
    rows = client.run_report(
        [_SCREEN_DIM], ["activeUsers", "screenPageViews"], start, end
    )

    # Soma por rótulo normalizado (a dimensão pode ter sido trocada no fallback;
    # qualquer que seja, a chave continua sendo o primeiro campo de dimensão).
    por_tela: dict[str, dict] = {}
    for r in rows:
        label = next((v for k, v in r.items() if k not in ("activeUsers", "screenPageViews")), "")
        chave = _norm(label)
        agg = por_tela.setdefault(chave, {"pessoas": 0, "acessos": 0})
        agg["pessoas"] += int(r.get("activeUsers", 0) or 0)
        agg["acessos"] += int(r.get("screenPageViews", 0) or 0)

    resultado: dict[str, dict] = {}
    for categoria, rotulo in categorias_map.items():
        agg = por_tela.get(_norm(rotulo), {"pessoas": 0, "acessos": 0})
        resultado[categoria] = {
            "tela": rotulo,
            "pessoas": agg["pessoas"],
            "acessos": agg["acessos"],
        }
    return resultado
