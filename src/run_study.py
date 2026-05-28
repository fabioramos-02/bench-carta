"""Orquestrador da Fase 2 — extrai dados Matomo e calcula o resultado.

Responsabilidade única: coordenar queries + métricas + persistência. Não contém
regra de cálculo (delega a analysis.metrics) nem transporte (delega a matomo.*).

Usa UM snapshot de getPageUrls (leve mesmo em period='year'). Visitas de serviço
exclusivo de cada perfil = proxy do uso do filtro de Perfil.

Uso:
    set MATOMO_TOKEN=...   (ou .env)
    python -m src.run_study
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from src.analysis.metrics import build_result
from src.matomo.client import get_client
from src.matomo.queries import fetch_page_index, home_visits, service_visits
from src.profiles import HIGHLIGHTED_SERVICES, shared_services, unique_services

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# Janela do estudo: ano de 2025 completo (determinística, ignora overrides do .env).
STUDY_WINDOW = {"period": "year", "date": "2025-01-01"}


def run() -> None:
    client = get_client()
    index = fetch_page_index(client, **STUDY_WINDOW)
    visitors = home_visits(index)

    rows = _collect_rows(index)
    per_profile = _attributable_totals(index)

    result = build_result(visitors, per_profile)
    _write_csv(rows)
    _print_summary(result)


def _collect_rows(index: dict[str, int]) -> list[dict]:
    """Linha por (perfil, serviço) com visitas e flag de atribuição."""
    shared = shared_services()
    rows: list[dict] = []
    for profile, services in HIGHLIGHTED_SERVICES.items():
        for label, path in services.items():
            rows.append(
                {
                    "perfil": profile,
                    "servico": label,
                    "path": path,
                    "visitas": service_visits(index, path),
                    "exclusivo": path not in shared,
                }
            )
    return rows


def _attributable_totals(index: dict[str, int]) -> dict[str, int]:
    """Soma de visitas dos serviços exclusivos, por perfil atribuível."""
    totals: dict[str, int] = {}
    for profile, services in unique_services().items():
        if not services:
            continue
        totals[profile] = sum(service_visits(index, p) for p in services.values())
    return totals


def _write_csv(rows: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / "uso-filtro-perfil-2025.csv"
    fields = ["perfil", "servico", "path", "visitas", "exclusivo"]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV salvo: {out}")


def _print_summary(result) -> None:
    print("\n=== Uso do Filtro de Perfil (base 2025) ===")
    print(f"Visitas da home: {result.home_visitors}")
    print(f"Visitas atribuíveis (serviços exclusivos): {result.attributable_interactions}")
    print(f"Taxa de adoção: {result.adoption_rate:.2%} (limiar {result.threshold:.0%})")
    print("Distribuição entre perfis atribuíveis:")
    for profile, share in result.distribution.items():
        print(f"  - {profile}: {share:.1%} ({result.per_profile_counts[profile]})")
    print(f"\n>>> RECOMENDAÇÃO: {result.recommendation}")


if __name__ == "__main__":
    run()
