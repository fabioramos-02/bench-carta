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


def mes_para_datas(mes: str) -> tuple[str, str, str]:
    """(matomo_date, ga_start, ga_end) para o mês YYYY-MM.

    Matomo: period='month' + date=<primeiro dia> → único do mês.
    GA4: start=<primeiro dia>, end=<último dia do mês ou hoje, o que vier antes>.
    """
    ano, m = (int(x) for x in mes.split("-"))
    primeiro = date(ano, m, 1)
    ultimo = date(ano, m, calendar.monthrange(ano, m)[1])
    fim = min(ultimo, date.today())
    return primeiro.isoformat(), primeiro.isoformat(), fim.isoformat()


def _primeiro_dia(parte: str) -> date:
    """Aceita 'YYYY-MM' ou 'YYYY-MM-DD' e devolve a data correspondente."""
    parte = parte.strip()
    if len(parte) == 7:  # YYYY-MM → primeiro dia do mês
        parte += "-01"
    return date.fromisoformat(parte)


def meses_no_intervalo(periodo: str) -> list[str]:
    """Meses YYYY-MM cobertos por um período do filtro, do início ao fim.

    Aceita data única ('YYYY-MM' ou 'YYYY-MM-DD' → 1 mês) ou range
    'INICIO,FIM' → todos os meses entre início e fim, inclusive. Visitante
    único só vem em período fechado (month); range multi-mês é quebrado em
    meses para somar mês-a-mês.
    """
    partes = periodo.split(",")
    inicio = _primeiro_dia(partes[0])
    fim = _primeiro_dia(partes[-1])
    meses: list[str] = []
    ano, m = inicio.year, inicio.month
    while (ano, m) <= (fim.year, fim.month):
        meses.append(f"{ano:04d}-{m:02d}")
        m += 1
        if m > 12:
            ano, m = ano + 1, 1
    return meses


def _linhas_paginas(matomo, period: str, date: str, rotulo: str) -> list[dict]:
    """Uma chamada de visitante único por página de WORKSPACE_PAGES.

    Período fechado (day/week/month/year) → único válido em chamada única.
    Falha de uma página (ex.: 504) é isolada: a linha sai zerada e o painel
    segue, em vez de derrubar a seção inteira.
    """
    from src.matomo.queries import page_unique_visitors

    rows: list[dict] = []
    for nome, url in WORKSPACE_PAGES.items():
        try:
            pessoas, acessos = page_unique_visitors(matomo, url, period=period, date=date)
        except Exception:  # noqa: BLE001 — isola falha por página
            pessoas, acessos = 0, 0
        rows.append({"categoria": nome, "pessoas": pessoas, "acessos": acessos, "periodo": rotulo})
    return rows


def compute_portal(window: dict | str | None = None) -> list[dict]:
    """Páginas do Portal (Matomo): pessoas únicas por categoria. Para o painel.

    `window` é a janela do filtro lateral:
      - dict {period, date} — period em day/week/month/year/range;
      - str  — 'YYYY-MM', 'YYYY-MM-DD' ou range 'INICIO,FIM' (compat. legado);
      - None — mês corrente.

    O Matomo calcula único em qualquer período fechado (day/week/month/year),
    então a consulta respeita o período do filtro: 1 chamada por página, com a
    varredura do tamanho da janela (semana = 7 dias, não o mês inteiro). Só o
    'range' (intervalo livre) devolve único zerado; aí o período é quebrado em
    meses e somado mês-a-mês — soma que superestima quem ficou ativo em mais de
    um mês (aproximação, não cohort deduplicada).
    """
    if isinstance(window, dict):
        period = window.get("period", "month")
        date_str = window.get("date") or _mes_alvo()
    else:  # str legado ou None
        period = "range" if window and "," in window else "month"
        date_str = window or _mes_alvo()

    from src.matomo.client import get_client

    matomo = get_client()

    if period == "range":
        meses = meses_no_intervalo(date_str)
        rotulo = meses[0] if len(meses) == 1 else f"{meses[0]}..{meses[-1]}"
        acc: dict[str, dict] = {}
        for mes in meses:
            for r in _linhas_paginas(matomo, "month", f"{mes}-01", rotulo):
                a = acc.setdefault(
                    r["categoria"],
                    {"categoria": r["categoria"], "pessoas": 0, "acessos": 0, "periodo": rotulo},
                )
                a["pessoas"] += r["pessoas"]
                a["acessos"] += r["acessos"]
        return list(acc.values())

    # day/week/month/year → período fechado em chamada única por página.
    date_norm = date_str.split(",")[0]
    return _linhas_paginas(matomo, period, date_norm, date_norm)


def compute_acessos(mes: str | None = None) -> list[dict]:
    """Coleta linhas de acessos das duas fontes. Núcleo sem I/O de arquivo."""
    mes = mes or _mes_alvo()
    matomo_date, ga_start, ga_end = mes_para_datas(mes)
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
