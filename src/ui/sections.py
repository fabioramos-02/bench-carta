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
    st.plotly_chart(fig, width="stretch", theme="streamlit")


def workspace_funnel(rows: list[dict]) -> None:
    """Funil da área logada: Entrar (login gov.br) → Área logada → Meus Sistemas."""
    by = {r["categoria"]: r for r in rows}
    steps = [
        ("Meu Perfil", "Entrar · login gov.br"),
        ("Área logada", "Área logada"),
        ("Meus Sistemas", "Meus Sistemas"),
    ]
    y = [rotulo for _, rotulo in steps]
    x = [by.get(cat, {}).get("pessoas", 0) for cat, _ in steps]
    fig = go.Figure(
        go.Funnel(
            y=y,
            x=x,
            texttemplate="%{value:,.0f} (%{percentInitial:.0%})",
            marker={"color": [t.PRIMARY, t.COMPARTILHADO, t.EXCLUSIVO]},
        )
    )
    fig.update_layout(height=280, margin={"l": 8, "r": 8, "t": 8, "b": 8}, separators=",.")
    st.plotly_chart(fig, width="stretch", theme="streamlit")


_WS_TREND_COLOR = {"Meu Perfil": t.PRIMARY, "Meus Sistemas": t.COMPARTILHADO}


def workspace_trend(serie: list[dict]) -> None:
    """Tendência mensal da área logada: pessoas por mês, Perfil × Sistemas.

    Áreas SOBREPOSTAS (não empilhadas): Meus Sistemas é etapa-abaixo de Meu
    Perfil no funil, não parcela aditiva. Perfil = envelope; Sistemas preenchido
    por baixo — leitura fiel do funil ao longo do tempo."""
    if not serie:
        return
    df = pd.DataFrame(serie)
    df = df[df["categoria"].isin(_WS_TREND_COLOR)]
    if df.empty:
        return
    df["rotulo"] = pd.to_datetime(df["mes"] + "-01").dt.strftime("%m/%Y")
    df = df.sort_values("mes")

    st.subheader("Evolução mês a mês — pessoas na área logada")
    fig = go.Figure()
    # Perfil primeiro (envelope maior), Sistemas por cima.
    for cat in ("Meu Perfil", "Meus Sistemas"):
        sub = df[df["categoria"] == cat]
        if sub.empty:
            continue
        cor = _WS_TREND_COLOR[cat]
        fig.add_trace(
            go.Scatter(
                x=sub["rotulo"],
                y=sub["pessoas"],
                name=cat,
                mode="lines+markers",
                line={"color": cor, "width": 2.5},
                fill="tozeroy",
                fillcolor=_rgba(cor, 0.18),
                hovertemplate="%{x}<br>%{y:,.0f} pessoas<extra>" + cat + "</extra>",
            )
        )
    fig.update_xaxes(title_text="")
    fig.update_yaxes(separatethousands=True, rangemode="tozero")
    fig.update_layout(
        height=320, margin={"l": 8, "r": 16, "t": 8, "b": 8}, separators=",.",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "x": 0},
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch", theme="streamlit")


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


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
    st.plotly_chart(fig, width="stretch", theme="streamlit")
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
    st.plotly_chart(fig, width="stretch", theme="streamlit")


