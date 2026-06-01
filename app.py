"""BI institucional — Uso do Filtro de Perfil no Portal Único.

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
from src.run_acessos import compute_workspace
from src.run_study import compute
from src.ui import PROFILE_LABEL, app_view, cards, sections
from src.ui import sidebar as sb
from src.ui import theme

st.set_page_config(page_title="BI · Portal Único — SETDIG", layout="wide")


@st.cache_data(ttl=3600, show_spinner="Consultando Matomo...")
def load(window: dict):
    result, rows, _ = compute(window)
    df = pd.DataFrame(rows)
    df["perfil_label"] = df["perfil"].map(PROFILE_LABEL).fillna(df["perfil"])
    return result, df


def _painel_filtro() -> None:
    window, label = sb.period_selector()
    theme.header(
        "BI — Uso do Filtro de Perfil no Portal Único",
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
def _load_workspace(period: str, date: str):
    return compute_workspace({"period": period, "date": date})


def _ws_pessoas(resumo: list[dict], categoria: str) -> int:
    return next((r["pessoas"] for r in resumo if r["categoria"] == categoria), 0)


def _delta_mensal(serie: list[dict], categoria: str) -> str | None:
    """Variação % do último mês vs o penúltimo, para st.metric. None se <2 meses."""
    pts = sorted(
        (p for p in serie if p["categoria"] == categoria), key=lambda p: p["mes"]
    )
    if len(pts) < 2 or not pts[-2]["pessoas"]:
        return None
    var = (pts[-1]["pessoas"] - pts[-2]["pessoas"]) / pts[-2]["pessoas"]
    return f"{var:+.1%}".replace(".", ",")


def _narrativa(serie: list[dict]) -> str:
    """Frase de tendência do período: variação ponta-a-ponta + mês de pico (Meu Perfil)."""
    pts = sorted(
        (p for p in serie if p["categoria"] == "Meu Perfil"), key=lambda p: p["mes"]
    )
    if len(pts) < 2:
        return ""
    ini, fim = pts[0]["pessoas"], pts[-1]["pessoas"]
    pico = max(pts, key=lambda p: p["pessoas"])
    pico_lbl = f"{pico['mes'][5:7]}/{pico['mes'][:4]}"
    if ini:
        var = (fim - ini) / ini
        rumo = "subiu" if var > 0.005 else "caiu" if var < -0.005 else "ficou estável"
        tend = f" Os logins via gov.br **{rumo}** {abs(var):.0%} de ponta a ponta no período."
    else:
        tend = ""
    return f"{tend} Pico em **{pico_lbl}** ({_br(pico['pessoas'])} pessoas)."


def _br(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def _secao_workspace(window: dict) -> None:
    """Área logada do portal (gov.br): Entrar → Meu Perfil → Meus Sistemas.

    Respeita o período do filtro. day/week/month → 1 chamada/página. year e range
    → série mensal de consultas leves somada (evita a query de ano que estoura 504)
    e habilita o gráfico de tendência mês a mês."""
    period = window.get("period", "month")
    date_str = window.get("date", "") or date.today().strftime("%Y-%m")
    st.markdown("### Área logada ms.gov.br")
    st.caption(
        "Jornada do cidadão autenticado: clica em **Entrar** e loga com a conta "
        "**gov.br** (Meu Perfil) → entra na **Área logada** → abre **Meus Sistemas**."
    )
    try:
        data = _load_workspace(period, date_str)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Workspace indisponível: {exc}")
        return
    resumo, serie, multi_mes = data["resumo"], data["serie"], data["multi_mes"]
    rotulo = data["rotulo"]

    # KPIs com delta mês-a-mês (delta só quando há série de >1 mês).
    k1, k2 = st.columns(2)
    k1.metric(
        "Meu Perfil — pessoas", _br(_ws_pessoas(resumo, "Meu Perfil")),
        delta=_delta_mensal(serie, "Meu Perfil") if multi_mes else None,
        help="Login via gov.br no período. Delta = último mês vs anterior.",
    )
    k2.metric(
        "Meus Sistemas — pessoas", _br(_ws_pessoas(resumo, "Meus Sistemas")),
        delta=_delta_mensal(serie, "Meus Sistemas") if multi_mes else None,
        help="Abriram Meus Sistemas no período. Delta = último mês vs anterior.",
    )

    sections.workspace_funnel(resumo)
    if multi_mes:
        sections.workspace_trend(serie)

    cards.workspace_cards(resumo, rotulo)
    nota_soma = (
        " Como o período cobre vários meses, os únicos são somados mês a mês — quem "
        "ficou ativo em mais de um mês conta mais de uma vez (aproximação)."
        if multi_mes else ""
    )
    st.info(
        "**Como ler:** o funil cai a cada passo — da multidão que faz login via "
        "gov.br, uma fração entra na área logada e uma fração menor abre Meus "
        "Sistemas. *Pessoas* = visitantes únicos no período do filtro." + nota_soma +
        _narrativa(serie),
        icon=":material/lightbulb:",
    )


def _painel_acessos() -> None:
    theme.header(
        "MS Digital — Categorias e Serviços do App",
        "Governo de MS · SETDIG · GA4 · pessoas por categoria · nativo × redirecionado",
    )
    app_view.render()


_PAINEIS = {
    "Portal Único": _painel_filtro,
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
