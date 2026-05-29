"""Seletor de período (calendário) — padrão do projeto matomo.

Responsabilidade única: coletar a janela de análise via calendário e devolver
o par (window p/ a API Matomo, rótulo legível). Sem chamadas de dados.
"""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

_PERIOD_MAP = {
    "Dia": "day",
    "Semana": "week",
    "Mês": "month",
    "Ano": "year",
    "Intervalo de datas": "range",
}


def period_selector() -> tuple[dict, str]:
    """Sidebar com calendário DD/MM/YYYY → ({period, date}, rótulo)."""
    st.sidebar.header("Período")
    label = st.sidebar.radio("Agregação", list(_PERIOD_MAP), index=2)  # default: Mês
    period = _PERIOD_MAP[label]
    hoje = date.today()

    if period == "range":
        col1, col2 = st.sidebar.columns(2)
        inicio = col1.date_input(
            "Início", value=hoje.replace(day=1), max_value=hoje, format="DD/MM/YYYY"
        )
        fim = col2.date_input(
            "Fim", value=hoje, max_value=hoje, format="DD/MM/YYYY"
        )
        if inicio > fim:
            st.sidebar.error("Data de início maior que a fim.")
            st.stop()
        rng = f"{inicio:%Y-%m-%d},{fim:%Y-%m-%d}"
        return {"period": "range", "date": rng}, f"{inicio:%d/%m/%Y}–{fim:%d/%m/%Y}"

    ref = st.sidebar.date_input(
        "Data de referência", value=hoje, max_value=hoje, format="DD/MM/YYYY"
    )
    window = {"period": period, "date": ref.strftime("%Y-%m-%d")}
    return window, _humanize(period, ref)


def _humanize(period: str, ref: date) -> str:
    if period == "year":
        return f"ano de {ref.year}"
    if period == "month":
        return f"{ref:%m/%Y}"
    if period == "week":
        ini = ref - timedelta(days=ref.weekday())
        return f"semana de {ini:%d/%m/%Y}"
    return f"{ref:%d/%m/%Y}"
