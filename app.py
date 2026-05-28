"""Dashboard Streamlit — Uso do Filtro de Perfil no Portal MS (base 2025).

Responsabilidade única: apresentação. Consome `run_study.compute()` (cacheado)
e renderiza indicadores, gráficos e a recomendação. Sem regra de cálculo aqui.

Uso:
    streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import PORTAL_BASE_URL
from src.run_study import STUDY_WINDOW, compute

st.set_page_config(page_title="Filtro de Perfil — Portal MS", layout="wide")

PROFILE_LABEL = {
    "CIDADAO": "Cidadão",
    "SERVIDOR_PUBLICO": "Servidor Público",
    "EMPRESA": "Empresa",
    "GESTAO_PUBLICA": "Gestão Pública",
}


@st.cache_data(ttl=3600, show_spinner="Consultando Matomo (ano 2025)...")
def load():
    result, rows, _ = compute(STUDY_WINDOW)
    df = pd.DataFrame(rows)
    df["perfil"] = df["perfil"].map(PROFILE_LABEL).fillna(df["perfil"])
    return result, df


def main() -> None:
    st.title("Uso do Filtro de Perfil — Portal de Serviços MS")
    st.caption(
        "Abas *Serviços em Destaque* (Cidadão / Servidor / Empresa / Gestão). "
        "Base: ano de 2025 · Matomo idSite=298."
    )

    try:
        result, df = load()
    except Exception as exc:  # noqa: BLE001 — superfície de erro amigável
        st.error(f"Falha ao consultar o Matomo: {exc}")
        st.info("Defina MATOMO_TOKEN no .env e tente novamente.")
        return

    _kpis(result)
    st.divider()
    _recommendation(result)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        _distribution_chart(result)
    with col2:
        _services_chart(df)
    st.divider()
    _services_table(df)
    _footnotes()


def _kpis(result) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Visitas da home", f"{result.home_visitors:,}".replace(",", "."))
    c2.metric("Visitas atribuíveis", f"{result.attributable_interactions:,}".replace(",", "."))
    c3.metric("Proxy ingênuo", f"{result.proxy_rate:.2%}", help="Limite superior inflado")
    c4.metric(
        "Taxa corrigida",
        f"{result.corrected_rate:.3%}",
        delta=f"limiar {result.threshold:.0%}",
        delta_color="off",
    )


def _recommendation(result) -> None:
    if result.recommendation == "MANTER":
        st.success(f"### Recomendação: MANTER  ·  taxa {result.corrected_rate:.3%} ≥ {result.threshold:.0%}")
    else:
        st.error(
            f"### Recomendação: REMOVER  ·  taxa corrigida {result.corrected_rate:.3%} "
            f"<< limiar {result.threshold:.0%}"
        )
        st.caption(
            "Proxy ingênuo conta tráfego direto/busca sem relação com o filtro. "
            f"Correção: só ~{result.home_fraction:.1%} dos acessos vêm da home."
        )


def _distribution_chart(result) -> None:
    st.subheader("Distribuição entre perfis atribuíveis")
    data = pd.DataFrame(
        {
            "Perfil": [PROFILE_LABEL.get(p, p) for p in result.per_profile_counts],
            "Visitas": list(result.per_profile_counts.values()),
        }
    )
    fig = px.bar(data, x="Perfil", y="Visitas", text="Visitas", color="Perfil")
    fig.update_traces(
        texttemplate="%{y:,.0f}", textposition="auto", textfont_size=12, cliponaxis=False
    )
    fig.update_yaxes(separatethousands=True)
    fig.update_layout(
        showlegend=False,
        height=380,
        uniformtext_minsize=10,
        uniformtext_mode="hide",
        separators=",.",  # pt-BR: decimal ',' milhar '.'
    )
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")
    st.caption("Empresa e Gestão Pública: sem serviço exclusivo → não atribuíveis.")


# Cores acessíveis (contraste AA em tema claro e escuro)
_TIPO_COLORS = {"Exclusivo": "#0E9F8E", "Compartilhado": "#9AA0A6"}


def _services_chart(df: pd.DataFrame) -> None:
    st.subheader("Top serviços em destaque por visitas (2025)")
    # 1 barra por serviço: dedupe por path mantendo maior visita e o flag exclusivo
    dedup = (
        df.sort_values("visitas", ascending=False)
        .drop_duplicates(subset="path", keep="first")
        .head(10)
        .copy()
    )
    dedup["tipo"] = dedup["exclusivo"].map({True: "Exclusivo", False: "Compartilhado"})
    fig = px.bar(
        dedup,
        x="visitas",
        y="servico",
        color="tipo",
        orientation="h",
        text="visitas",
        color_discrete_map=_TIPO_COLORS,
        labels={"servico": "", "visitas": "Visitas", "tipo": "Tipo"},
    )
    fig.update_traces(
        texttemplate="%{x:,.0f}", textposition="auto", textfont_size=12, cliponaxis=False
    )
    fig.update_xaxes(separatethousands=True)
    fig.update_layout(
        height=400,
        yaxis={"categoryorder": "total ascending"},
        legend_title_text="Tipo",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
        margin={"l": 8, "r": 24, "t": 8, "b": 8},
        separators=",.",  # pt-BR: decimal ',' milhar '.'
    )
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")


def _services_table(df: pd.DataFrame) -> None:
    st.subheader("Serviços em destaque — detalhe")
    show = df.copy()
    show["link"] = PORTAL_BASE_URL + show["path"]
    show["exclusivo"] = show["exclusivo"].map({True: "Sim", False: "Compartilhado"})
    st.dataframe(
        show[["perfil", "servico", "visitas", "exclusivo", "link"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "perfil": "Perfil",
            "servico": "Serviço",
            "visitas": st.column_config.NumberColumn("Visitas", format="%d"),
            "exclusivo": "Atribuível",
            "link": st.column_config.LinkColumn("Link"),
        },
    )


def _footnotes() -> None:
    with st.expander("Notas metodológicas e limitações"):
        st.markdown(
            "- A troca de aba é **DOM swap** (sem evento/pageview) → invisível ao Matomo.\n"
            "- Medição por *proxy*: visitas a serviços exclusivos de cada perfil.\n"
            "- **Proxy ingênuo** conta tráfego direto/busca; **taxa corrigida** aplica a "
            "fração média que vem da home (amostra Transitions: 0,95–2,47%).\n"
            "- `Transitions` por ano/mês retorna 504 no servidor → correção via amostra diária.\n"
            "- Para número exato: instrumentar *event tracking* no clique da aba."
        )


if __name__ == "__main__":
    main()
