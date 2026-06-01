"""BI institucional — Uso do Filtro de Perfil no Portal MS.

Responsabilidade única: orquestração da apresentação. Tema e componentes vivem
em `src/ui/*`; dados/cálculo em `src/*`. Período é dinâmico (calendário).

Uso:
    streamlit run app.py
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.obs import setup_logging
from src.run_acessos import compute_portal
from src.run_study import compute
from src.ui import PROFILE_LABEL, app_view, cards, sections
from src.ui import sidebar as sb
from src.ui import theme

st.set_page_config(page_title="BI · Portal MS — SETDIG", layout="wide")


@st.cache_data(ttl=3600, show_spinner="Consultando Matomo...")
def load(window: dict):
    result, rows, _ = compute(window)
    df = pd.DataFrame(rows)
    df["perfil_label"] = df["perfil"].map(PROFILE_LABEL).fillna(df["perfil"])
    return result, df


def _painel_filtro() -> None:
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
    col1, col2 = st.columns(2)
    with col1:
        sections.distribution_chart(result)
    with col2:
        sections.services_chart(df)
    st.divider()
    cards.service_cards(df)
    st.divider()
    _secao_workspace(window)


@st.cache_data(ttl=3600, show_spinner="Consultando Matomo (workspace)...")
def _load_portal(period: str, date: str):
    return compute_portal({"period": period, "date": date})


def _secao_workspace(window: dict) -> None:
    """Área logada do portal (gov.br): Entrar → Meu Perfil → Meus Sistemas.

    Respeita o período do filtro lateral. O Matomo calcula único em qualquer
    período fechado (day/week/month/year) → 1 chamada por página; só o range
    (intervalo livre) zera o único, daí é somado mês-a-mês."""
    period = window.get("period", "month")
    date_str = window.get("date", "") or date.today().strftime("%Y-%m")
    st.markdown("### Área logada ms.gov.br")
    st.caption(
        "Jornada do cidadão autenticado: clica em **Entrar** e loga com a conta "
        "**gov.br** (Meu Perfil) → entra na **Área logada** → abre **Meus Sistemas**."
    )
    try:
        rows = _load_portal(period, date_str)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Workspace indisponível: {exc}")
        return
    rotulo = rows[0].get("periodo", date_str) if rows else date_str
    sections.workspace_funnel(rows)
    cards.workspace_cards(rows, rotulo)
    nota_range = (
        " Para *intervalo livre* o Matomo zera o único, então é somado mês-a-mês — "
        "quem ficou ativo em mais de um mês conta mais de uma vez."
        if period == "range" else ""
    )
    st.info(
        "**Como ler:** o funil cai a cada passo — da multidão que faz login via "
        "gov.br, uma fração entra na área logada e uma fração menor abre Meus "
        "Sistemas. *Pessoas* = visitantes únicos no período do filtro." + nota_range +
        " Contagem por página, não cohort fechada: os degraus são aproximados, não "
        "subconjuntos exatos.",
        icon=":material/lightbulb:",
    )


def _painel_acessos() -> None:
    theme.header(
        "MS Digital — Categorias e Serviços do App",
        "Governo de MS · SETDIG · GA4 · pessoas por categoria · nativo × redirecionado",
    )
    app_view.render()


_PAINEIS = {
    "Portal MS": _painel_filtro,
    "MS Digital APP": _painel_acessos,
}


def main() -> None:
    setup_logging()
    theme.inject_css()
    st.sidebar.header("Painel")
    escolha = st.sidebar.radio("Selecione", list(_PAINEIS), label_visibility="collapsed")
    _PAINEIS[escolha]()


if __name__ == "__main__":
    main()
