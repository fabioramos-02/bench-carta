"""Consultas de domínio sobre a API Matomo para o estudo do filtro de Perfil.

Responsabilidade única: traduzir perguntas do estudo em chamadas concretas da
Reporting API e devolver números limpos. Sem cálculo de métrica (fica em
`analysis.metrics`) e sem transporte (fica em `matomo.client`).

Estratégia de performance: um único `Actions.getPageUrls` (flat) cobre o site
inteiro no período, de onde se extraem tanto a home quanto cada serviço. Evita N
chamadas pesadas em períodos longos (period='year').
"""
from __future__ import annotations

from typing import Any

from src.config import PORTAL_BASE_URL
from src.matomo.client import MatomoClient


def fetch_page_index(client: MatomoClient, **window: Any) -> dict[str, int]:
    """Mapa caminho-normalizado -> visitas, num único getPageUrls (flat)."""
    rows = client.call("Actions.getPageUrls", flat=1, filter_limit=-1, **window)
    index: dict[str, int] = {}
    for row in rows if isinstance(rows, list) else []:
        # 'label' já vem como caminho limpo (ex.: '/seguranca/...'); 'url' pode
        # vir como 'http://ms.gov.br/' (sem www). Preferir label.
        key = _normalize(row.get("label") or row.get("url") or "")
        visits = int(row.get("nb_visits") or row.get("nb_hits") or 0)
        index[key] = index.get(key, 0) + visits
    return index


def home_visits(index: dict[str, int]) -> int:
    """Visitas da home (denominador da taxa de adoção)."""
    return index.get("/", 0) or index.get("/index", 0)


def service_visits(index: dict[str, int], path: str) -> int:
    """Visitas de um serviço específico a partir do snapshot."""
    return index.get(_normalize(path), 0)


def transitions_from_home(client: MatomoClient, path: str, **window: Any) -> int:
    """Enriquecimento opcional: visitas chegando ao serviço vindas da home.

    Pesado em períodos longos (1 chamada por serviço). Usar só sob demanda.
    LIMITE SUPERIOR do uso do filtro: inclui menu/busca, não só o card.
    """
    data = client.call(
        "Transitions.getTransitionsForPageUrl",
        pageUrl=f"{PORTAL_BASE_URL}{path}",
        **window,
    )
    total = 0
    for prev in data.get("previousPages", []) if isinstance(data, dict) else []:
        if _is_home(prev.get("url") or prev.get("label") or ""):
            total += int(prev.get("referrals") or 0)
    return total


def _normalize(url: str) -> str:
    u = (url or "").strip().lower().rstrip("/")
    for scheme in ("https://", "http://"):
        if u.startswith(scheme):
            u = u[len(scheme):]
    for host in ("www.ms.gov.br", "ms.gov.br"):
        if u.startswith(host):
            u = u[len(host):]
    if u.startswith("/index"):
        u = u[len("/index"):]
    return "/" + u.lstrip("/")


def _is_home(url: str) -> bool:
    # Transitions rotula a home como 'ms.gov.br/' (sem esquema). _normalize cobre.
    return _normalize(url) in ("/", "/index", "")
