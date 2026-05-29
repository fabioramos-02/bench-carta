"""Orquestrador: acessos por categoria -> CSV para o BI.

Responde à demanda da chefia com dois recortes, num único CSV:
  - Portal (Matomo): pessoas únicas em /workspace e /workspace/minha-area/meus-sistemas.
  - MS Digital (GA4): pessoas na categoria "servidor" (tela Servidor Público) e
    "holerite" (tela Contracheque).

Responsabilidade única: coordenar queries (matomo + ga4) + persistência. Sem
regra de cálculo nem transporte.

Uso:
    set MATOMO_TOKEN=... e credenciais GOOGLE_* (ou .env)
    python -m src.run_acessos
"""
from __future__ import annotations

import calendar
import csv
import os
from datetime import date
from pathlib import Path

from src.config import MS_DIGITAL_CATEGORIAS, WORKSPACE_PAGES
from src.obs import setup_logging

setup_logging()
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _mes_alvo() -> str:
    """Mês da consulta no formato YYYY-MM. Default: mês corrente.

    Mês é a granularidade necessária porque o Matomo só calcula visitantes
    únicos em períodos fechados (day/week/month/year) — em 'range' devolve 0.
    """
    env = os.getenv("ACESSOS_MONTH", "").strip()
    return env or date.today().strftime("%Y-%m")


def _datas_do_mes(mes: str) -> tuple[str, str, str]:
    """(matomo_date, ga_start, ga_end) para o mês YYYY-MM.

    Matomo: period='month' + date=<primeiro dia> → único do mês.
    GA4: start=<primeiro dia>, end=<último dia do mês ou hoje, o que vier antes>.
    """
    ano, m = (int(x) for x in mes.split("-"))
    primeiro = date(ano, m, 1)
    ultimo = date(ano, m, calendar.monthrange(ano, m)[1])
    fim = min(ultimo, date.today())
    return primeiro.isoformat(), primeiro.isoformat(), fim.isoformat()


def compute_acessos(mes: str | None = None) -> list[dict]:
    """Coleta linhas de acessos das duas fontes. Núcleo sem I/O de arquivo."""
    mes = mes or _mes_alvo()
    matomo_date, ga_start, ga_end = _datas_do_mes(mes)
    rows: list[dict] = []

    # --- Portal (Matomo) — único só vem em period=month ----------------------
    from src.matomo.client import get_client
    from src.matomo.queries import page_unique_visitors

    matomo = get_client()
    for nome, url in WORKSPACE_PAGES.items():
        pessoas, acessos = page_unique_visitors(
            matomo, url, period="month", date=matomo_date
        )
        rows.append(
            {
                "fonte": "Portal (MS GovBR)",
                "categoria": nome,
                "pessoas": pessoas,
                "acessos": acessos,
                "periodo": mes,
            }
        )

    # --- MS Digital (GA4) ----------------------------------------------------
    from src.ga4.client import get_ga4_client
    from src.ga4.queries import categoria_acessos

    ga = get_ga4_client()
    resultado = categoria_acessos(ga, MS_DIGITAL_CATEGORIAS, ga_start, ga_end)
    for categoria, dados in resultado.items():
        rows.append(
            {
                "fonte": "MS Digital",
                "categoria": categoria,
                "pessoas": dados["pessoas"],
                "acessos": dados["acessos"],
                "periodo": mes,
            }
        )

    return rows


def run() -> None:
    rows = compute_acessos()
    _write_csv(rows)
    _print_summary(rows)


def _write_csv(rows: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / "acessos-categorias.csv"
    fields = ["fonte", "categoria", "pessoas", "acessos", "periodo"]
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV salvo: {out}")


def _print_summary(rows: list[dict]) -> None:
    print("\n=== Acessos por categoria ===")
    for r in rows:
        print(
            f"  [{r['fonte']}] {r['categoria']}: "
            f"{r['pessoas']} pessoas / {r['acessos']} acessos ({r['periodo']})"
        )


if __name__ == "__main__":
    run()
