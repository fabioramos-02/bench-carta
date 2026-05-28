"""BI institucional — Uso do Filtro de Perfil no Portal MS.

Responsabilidade única: orquestração da apresentação. Tema e componentes vivem
em `src/ui/*`; dados/cálculo em `src/*`. Período é dinâmico (calendário).

Uso:
    streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.run_study import compute
from src.ui import PROFILE_LABEL, cards, sections
from src.ui import sidebar as sb
from src.ui import theme

st.set_page_config(page_title="BI · Filtro de Perfil — Portal MS", layout="wide")


@st.cache_data(ttl=3600, show_spinner="Consultando Matomo...")
def load(window: dict):
    result, rows, _ = compute(window)
    df = pd.DataFrame(rows)
    df["perfil_label"] = df["perfil"].map(PROFILE_LABEL).fillna(df["perfil"])
    return result, df


def main() -> None:
    theme.inject_css()
    window, label = sb.period_selector()
    theme.header(
        "BI — Uso do Filtro de Perfil no Portal de Serviços",
        f"Governo de MS · SETDIG · Matomo idSite=298 · Base: {label}",
    )

    try:
        result, df = load(window)
    except Exception as exc:  # noqa: BLE001 — superfície de erro amigável
        st.error(f"Falha ao consultar o Matomo: {exc}")
        st.info("Defina MATOMO_TOKEN no .env e tente novamente.")
        return

    sections.kpis(result)
    st.divider()
    sections.story(result)
    st.divider()
    sections.recommendation(result)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        sections.distribution_chart(result)
    with col2:
        sections.services_chart(df)
    st.divider()
    cards.service_cards(df)


if __name__ == "__main__":
    main()
