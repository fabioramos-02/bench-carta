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
