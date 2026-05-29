"""Painel: Acessos por categoria — MS Digital (GA4) + MS GovBR (Matomo).

Responsabilidade única: apresentar os números da demanda da chefia (quantas
pessoas acessam servidor/holerite no app e meus-sistemas no portal). Dados vêm
de `src.run_acessos.compute_acessos`; cálculo/transporte ficam nas camadas src.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src.run_acessos import compute_acessos
from src.ui import theme as t
from src.ui.sections import _br


@st.cache_data(ttl=3600, show_spinner="Consultando Matomo + GA4...")
def _load(mes: str) -> list[dict]:
    return compute_acessos(mes)


def _meses_recentes(n: int = 12) -> list[str]:
    """Últimos n meses no formato YYYY-MM, do mais recente ao mais antigo."""
    hoje = date.today()
    meses = []
    ano, m = hoje.year, hoje.month
    for _ in range(n):
        meses.append(f"{ano:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            ano -= 1
    return meses


def _pessoas(rows: list[dict], fonte: str, categoria: str) -> tuple[int, int]:
    for r in rows:
        if r["fonte"] == fonte and r["categoria"] == categoria:
            return r["pessoas"], r["acessos"]
    return 0, 0


def render() -> None:
    mes = st.selectbox("Mês de referência", _meses_recentes(), index=0)

    try:
        rows = _load(mes)
    except Exception as exc:  # noqa: BLE001 — superfície de erro amigável
        st.error(f"Falha ao consultar as APIs: {exc}")
        st.info(
            "Verifique MATOMO_TOKEN e as credenciais GOOGLE_* no .env. "
            "Detalhes técnicos em logs/api.log."
        )
        return

    serv_p, serv_a = _pessoas(rows, "MS Digital", "servidor")
    hol_p, hol_a = _pessoas(rows, "MS Digital", "holerite")
    sis_p, sis_a = _pessoas(rows, "Portal (MS GovBR)", "Meus Sistemas")
    perf_p, perf_a = _pessoas(rows, "Portal (MS GovBR)", "Meu Perfil")

    st.subheader("App MS Digital")
    c1, c2 = st.columns(2)
    c1.metric("Servidor Público — pessoas", _br(serv_p),
              help=f"{_br(serv_a)} acessos (visualizações de tela) no mês.")
    c2.metric("Holerite (Contracheque) — pessoas", _br(hol_p),
              help=f"{_br(hol_a)} acessos (visualizações de tela) no mês.")

    st.subheader("Portal MS GovBR")
    c3, c4 = st.columns(2)
    c3.metric("Meus Sistemas — pessoas", _br(sis_p),
              help=f"{_br(sis_a)} visitas no mês.")
    c4.metric("Meu Perfil — pessoas", _br(perf_p),
              help=f"{_br(perf_a)} visitas no mês.")

    st.divider()

    df = pd.DataFrame(rows)
    fig = px.bar(
        df, x="categoria", y="pessoas", color="fonte", text="pessoas",
        barmode="group", labels={"categoria": "", "pessoas": "Pessoas", "fonte": "Fonte"},
        color_discrete_sequence=[t.PRIMARY, t.EXCLUSIVO],
    )
    fig.update_traces(texttemplate="%{y:,.0f}", textposition="auto", cliponaxis=False)
    fig.update_yaxes(separatethousands=True)
    fig.update_layout(height=400, separators=",.", legend_title_text="Fonte",
                      margin={"l": 8, "r": 8, "t": 8, "b": 8})
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    st.dataframe(
        df.rename(columns={
            "fonte": "Fonte", "categoria": "Categoria",
            "pessoas": "Pessoas", "acessos": "Acessos", "periodo": "Período",
        }),
        use_container_width=True, hide_index=True,
    )
    st.caption(
        "**Pessoas** = visitantes únicos no mês (Matomo `nb_uniq_visitors` / "
        "GA4 `activeUsers`). **Acessos** = visitas/visualizações (conta repetição). "
        "Granularidade mensal: o Matomo só calcula único em período fechado."
    )
