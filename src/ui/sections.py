"""Indicadores, narrativa e gráficos do estudo.

Responsabilidade única: traduzir o `StudyResult`/DataFrame em visual legível
para a gestão. Sem cálculo de negócio (vem de `analysis.metrics`).
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.ui import PROFILE_LABEL
from src.ui import theme as t


def _br(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def kpis(result) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Visitantes (home)", _br(result.home_visitors))
    c2.metric(
        "Acesso bruto",
        f"{result.proxy_rate:.2%}",
        help="Conta TODO mundo que abriu um serviço do perfil — inclusive quem chegou "
        "por Google, busca ou menu, não só pelo filtro. É um teto, não o uso real.",
    )
    c3.metric(
        "Uso real do filtro",
        f"{result.corrected_rate:.3%}",
        help="Só quem chegou ao serviço pela home, onde o filtro de Perfil fica.",
    )
    c4.metric("Meta mínima", f"{result.threshold:.0%}", help="Limiar de decisão.")


def story(result) -> None:
    """Narrativa de gestor: frase-âncora + funil + como ler."""
    rate = result.corrected_rate
    por_mil = max(rate * 1000, 0)
    um_a_cada = int(round(1 / rate)) if rate > 0 else 0
    real_abs = int(result.attributable_interactions * result.home_fraction)

    st.markdown(
        f"#### De cada **1.000** visitantes do portal, cerca de "
        f"**{por_mil:.0f}** usam o filtro de Perfil para chegar a um serviço."
    )
    st.caption(
        f"Ou seja: ~1 a cada {_br(um_a_cada)} pessoas. Estimado em **{_br(real_abs)}** "
        f"acessos via filtro no período."
    )

    _funnel(result)

    st.info(
        "**Como ler:** o número *bruto* parece grande porque soma quem chegou aos "
        "serviços do perfil por qualquer caminho (Google, busca, menu). Quando olhamos "
        "**só quem usou o filtro** (chegou pela home), o uso real é muito menor — por "
        "isso a recomendação se baseia no **uso real**, não no bruto.",
        icon=":material/lightbulb:",
    )


def _funnel(result) -> None:
    proxy_abs = result.attributable_interactions
    real_abs = int(proxy_abs * result.home_fraction)
    fig = go.Figure(
        go.Funnel(
            y=[
                "Visitantes do portal",
                "Abriram serviços do perfil",
                "Vieram de fato pelo filtro",
            ],
            x=[result.home_visitors, proxy_abs, real_abs],
            texttemplate="%{value:,.0f} (%{percentInitial})",
            marker={"color": [t.PRIMARY, t.COMPARTILHADO, t.EXCLUSIVO]},
        )
    )
    fig.update_layout(height=300, margin={"l": 8, "r": 8, "t": 8, "b": 8}, separators=",.")
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")


def distribution_chart(result) -> None:
    st.subheader("Distribuição entre perfis atribuíveis")
    data = pd.DataFrame(
        {
            "Perfil": [PROFILE_LABEL.get(p, p) for p in result.per_profile_counts],
            "Visitas": list(result.per_profile_counts.values()),
        }
    )
    fig = px.bar(data, x="Perfil", y="Visitas", text="Visitas", color="Perfil",
                 color_discrete_sequence=[t.PRIMARY, t.EXCLUSIVO, t.COMPARTILHADO])
    fig.update_traces(texttemplate="%{y:,.0f}", textposition="auto", textfont_size=12,
                      cliponaxis=False)
    fig.update_yaxes(separatethousands=True)
    fig.update_layout(showlegend=False, height=380, uniformtext_minsize=10,
                      uniformtext_mode="hide", separators=",.")
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")
    st.caption("Empresa e Gestão Pública: sem serviço exclusivo → não atribuíveis.")


_TIPO_COLORS = {"Exclusivo": t.EXCLUSIVO, "Compartilhado": t.COMPARTILHADO}


def services_chart(df: pd.DataFrame) -> None:
    st.subheader("Top serviços em destaque por visitas")
    dedup = (
        df.sort_values("visitas", ascending=False)
        .drop_duplicates(subset="path", keep="first")
        .head(10)
        .copy()
    )
    dedup["tipo"] = dedup["exclusivo"].map({True: "Exclusivo", False: "Compartilhado"})
    fig = px.bar(dedup, x="visitas", y="servico", color="tipo", orientation="h",
                 text="visitas", color_discrete_map=_TIPO_COLORS,
                 labels={"servico": "", "visitas": "Visitas", "tipo": "Tipo"})
    fig.update_traces(texttemplate="%{x:,.0f}", textposition="auto", textfont_size=12,
                      cliponaxis=False)
    fig.update_xaxes(separatethousands=True)
    fig.update_layout(height=400, yaxis={"categoryorder": "total ascending"},
                      legend_title_text="Tipo", uniformtext_minsize=10,
                      uniformtext_mode="hide", margin={"l": 8, "r": 24, "t": 8, "b": 8},
                      separators=",.")
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")


def recommendation(result) -> None:
    if result.recommendation == "MANTER":
        st.success(f"### Recomendação: MANTER · uso real {result.corrected_rate:.3%} "
                   f"≥ meta {result.threshold:.0%}")
    else:
        st.error(f"### Recomendação: REMOVER · uso real {result.corrected_rate:.3%} "
                 f"abaixo da meta de {result.threshold:.0%}")
