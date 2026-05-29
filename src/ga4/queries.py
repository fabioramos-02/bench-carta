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
