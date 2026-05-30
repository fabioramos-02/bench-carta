"""Explorador do app MS Digital: grade de categorias + drill-down + gráficos.

Responsabilidade única: apresentar `compute_app` no estilo da home do app
(ícones com quantitativo de pessoas) e, ao clicar, aprofundar nos serviços
(nativo × redirecionado). Sem cálculo/transporte.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ms_digital import compute_app
from src.ui import theme as t
from src.ui.sections import _br

_COLS = 4  # colunas na grade (mais estreito, igual à home do ms.gov.br)


@st.cache_data(ttl=3600, show_spinner="Consultando GA4 (app MS Digital)...")
def _load(start: str, end: str) -> dict:
    return compute_app(start, end)


_AGG = ["Dia", "Semana", "Mês", "Ano", "Intervalo de datas"]


def _periodo_ga() -> tuple[str, str, str]:
    """Seletor de período na sidebar, igual ao Portal MS: agregação + calendário
    'Data de referência'. GA4 aceita qualquer intervalo. Retorna (start, end, rótulo).
    """
    hoje = date.today()
    agg = st.sidebar.radio("Agregação", _AGG, index=2)  # default: Mês

    if agg == "Intervalo de datas":
        c1, c2 = st.sidebar.columns(2)
        ini = c1.date_input("Início", value=hoje.replace(day=1), max_value=hoje, format="DD/MM/YYYY")
        fim = c2.date_input("Fim", value=hoje, max_value=hoje, format="DD/MM/YYYY")
        if ini > fim:
            st.sidebar.error("Data de início maior que a fim.")
            st.stop()
        return ini.isoformat(), fim.isoformat(), f"{ini:%d/%m/%Y}–{fim:%d/%m/%Y}"

    ref = st.sidebar.date_input(
        "Data de referência", value=hoje, max_value=hoje, format="DD/MM/YYYY"
    )

    if agg == "Dia":
        return ref.isoformat(), ref.isoformat(), f"{ref:%d/%m/%Y}"
    if agg == "Semana":
        ini = ref - timedelta(days=ref.weekday())
        fim = min(ini + timedelta(days=6), hoje)
        return ini.isoformat(), fim.isoformat(), f"semana de {ini:%d/%m/%Y}"
    if agg == "Ano":
        ini = date(ref.year, 1, 1)
        fim = min(date(ref.year, 12, 31), hoje)
        return ini.isoformat(), fim.isoformat(), f"ano de {ref.year}"

    # Mês
    ini = date(ref.year, ref.month, 1)
    fim = min(date(ref.year, ref.month, calendar.monthrange(ref.year, ref.month)[1]), hoje)
    return ini.isoformat(), fim.isoformat(), f"{ref:%m/%Y}"


_ORDENAR = {
    "Pessoas (maior)": lambda c: -c["pessoas"],
    "Nome (A→Z)": lambda c: c["categoria"].lower(),
    "Nº de serviços": lambda c: -(c["n_nativo"] + c["n_redirect"]),
}
_TIPO_FILTRO = {"Todos": None, "Nativos": "nativo", "Redirecionados": "redirect"}


def render() -> None:
    # --- Filtros na lateral (mesma lógica do painel Portal MS) ---------------
    st.sidebar.header("Filtros")
    start, end, periodo_lbl = _periodo_ga()
    ordenar = st.sidebar.radio("Ordenar por", list(_ORDENAR), index=0)
    tipo_lbl = st.sidebar.radio("Tipo de serviço", list(_TIPO_FILTRO), index=0)
    tipo = _TIPO_FILTRO[tipo_lbl]

    try:
        dados = _load(start, end)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Falha ao consultar o GA4: {exc}")
        st.info("Confira as credenciais GOOGLE_* no .env. Detalhes em logs/api.log.")
        return

    categorias = sorted(dados["categorias"], key=_ORDENAR[ordenar])
    tot = dados["totais"]

    # --- Resumo --------------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Categorias", _br(tot["categorias"]))
    c2.metric("Serviços", _br(tot["total"]))
    c3.metric("Nativos", _br(tot["nativo"]),
              help="Telas do app (rastreadas como tela no GA4).")
    c4.metric("Redirecionados", _br(tot["redirect"]),
              help="Abrem o navegador (rastreados como clique no GA4).")
    st.divider()

    _storytelling(categorias, tot, periodo_lbl)
    st.divider()

    # --- Grade de categorias (estilo app) — clique no tile abre o modal ------
    st.markdown("### Categorias do app")
    st.caption("Número = pessoas únicas que usaram a categoria (qualquer serviço) no período. "
               "Clique no ícone para aprofundar.")
    cols = st.columns(_COLS)
    for i, c in enumerate(categorias):
        total_svc = c["n_nativo"] + c["n_redirect"]
        label = (f"**{c['categoria']}**  \n{_br(c['pessoas'])} pessoas · "
                 f"{total_svc} serviços")
        with cols[i % _COLS]:
            if st.button(label, icon=f":material/{c['icon']}:",
                         key=f"cat_{c['categoria']}", width="stretch"):
                st.session_state["modal_cat"] = c["categoria"]

    # Modal recomputado do run atual → acompanha o filtro (período/tipo) ao vivo.
    sel = st.session_state.get("modal_cat")
    if sel:
        cat_now = next((c for c in categorias if c["categoria"] == sel), None)
        if cat_now is not None:
            _modal(cat_now, tipo)
        else:
            st.session_state.pop("modal_cat", None)

    st.divider()
    _graficos(categorias, tot)
    st.caption(
        "**Pessoas** = usuários únicos no período (GA4 activeUsers). O total da categoria é a "
        "**união** desses únicos sobre todos os serviços — fica entre o maior serviço e a soma "
        "(não é a soma, pois a mesma pessoa não conta duas vezes). Serviços sem dado aparecem com 0."
    )


def _storytelling(categorias: list[dict], tot: dict, periodo: str) -> None:
    """Resumo em linguagem simples para a gestão (analista de dados)."""
    top = sorted(categorias, key=lambda c: c["pessoas"], reverse=True)[:3]
    top_txt = ", ".join(f"**{c['categoria']}** ({_br(c['pessoas'])})" for c in top)
    total = tot["total"] or 1
    pct_red = round(tot["redirect"] / total * 100)
    de_cada_10 = round(tot["redirect"] / total * 10)

    st.markdown("### Em resumo")
    st.markdown(
        f"Em **{periodo}**, o que o cidadão mais procurou no app foi: {top_txt} pessoas.\n\n"
        f"O app oferece **{_br(tot['total'])} serviços** em **{tot['categorias']} categorias**. "
        f"Desses, **{de_cada_10} de cada 10** ({pct_red}%) **abrem outro site** "
        f"(o app só encaminha); o restante são telas do próprio app."
    )
    st.info(
        "**Leitura rápida:** a maior parte dos serviços ainda leva o cidadão para fora "
        "do app. Trazer esses serviços para dentro tende a melhorar a experiência e "
        "permite medir melhor o uso.",
        icon=":material/lightbulb:",
    )


def _close_modal() -> None:
    """Limpa a seleção ao fechar (X / clique fora) — evita o modal reabrir sozinho."""
    st.session_state.pop("modal_cat", None)


# largura ~720px controlada por CSS (theme.py); on_dismiss limpa o estado no X.
@st.dialog("Serviços da categoria", on_dismiss=_close_modal)
def _modal(cat: dict, tipo: str | None = None) -> None:
    fonte_nota = {
        "uniao": " · pessoas únicas que usaram algum serviço da categoria",
        "tela": " · medido na tela da categoria no app",
        "clique": " · categoria redireciona direto (nº de cliques)",
        "servico": " · estimado pelo serviço de maior acesso",
    }.get(cat.get("pessoas_fonte", ""), "")
    st.markdown(f"### {cat['categoria']}")
    st.caption(
        f"{_br(cat['pessoas'])} pessoas únicas no período · "
        f"{cat['n_nativo']} nativos / {cat['n_redirect']} redirecionados{fonte_nota}"
    )
    _legenda_pessoas_acessos()
    servicos = [s for s in cat["servicos"] if tipo is None or s["tipo"] == tipo]
    if not servicos:
        st.info("Nenhum serviço para o filtro selecionado.")
    else:
        for s in servicos:
            _servico_card(s)
    if st.button("Fechar", key="modal_fechar"):
        st.session_state.pop("modal_cat", None)
        st.rerun()


def _legenda_pessoas_acessos() -> None:
    """Explica pessoas × acessos para a gestão (some a ambiguidade dos números)."""
    st.markdown(
        '<div class="metric-legend">'
        '<div class="ml-item"><span class="ml-k">Pessoas</span> = usuários '
        '<b>únicos</b> no período (cada cidadão conta 1×, mesmo abrindo várias vezes).</div>'
        '<div class="ml-item"><span class="ml-k">Acessos / Cliques</span> = total de '
        'aberturas (uma pessoa pode contar <b>várias</b> vezes).</div>'
        '<div class="ml-item">O total da categoria é a <b>união</b> dos únicos: fica '
        '<b>entre</b> o maior serviço e a soma — quem usa 2 serviços conta nos 2, mas '
        '1× na categoria.</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _servico_card(s: dict) -> None:
    """Linha compacta DS-MS. HTML em string única (sem indentação) para o
    Streamlit não interpretar o fechamento como bloco de código."""
    nativo = s["tipo"] == "nativo"
    tipo = "Nativo" if nativo else "Redirecionado"
    ic = "smartphone" if nativo else "open_in_new"
    link = (f'<a class="svc-lk" href="{s["url"]}" target="_blank">abrir ↗</a>'
            if s.get("url") else "")
    html = (
        '<div class="svc-row">'
        f'<span class="svc-ic">{ic}</span>'
        f'<div class="svc-main"><div class="svc-tipo">{tipo}</div>'
        f'<div class="svc-nm">{s["nome"]}</div></div>'
        f'<div class="svc-rt"><span class="svc-tag">{_br(s["pessoas"])} pessoas</span>'
        f'<span class="svc-mt">{_br(s["valor"])} {s["valor_label"]}</span>{link}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _graficos(categorias: list[dict], tot: dict) -> None:
    st.subheader("Pessoas por categoria")
    df = pd.DataFrame(
        [{"Categoria": c["categoria"], "Pessoas": c["pessoas"]} for c in categorias]
    )
    fig = px.bar(df, x="Pessoas", y="Categoria", orientation="h", text="Pessoas",
                 color_discrete_sequence=[t.PRIMARY])
    fig.update_traces(
        texttemplate="%{x:,.0f}", textposition="outside",
        textfont={"size": 15, "color": t.INK}, cliponaxis=False,
        marker_line_width=0,
    )
    fig.update_xaxes(separatethousands=True, showgrid=True, gridcolor=t.BORDER,
                     title=None, tickfont={"size": 14})
    fig.update_yaxes(categoryorder="total ascending", title=None,
                     tickfont={"size": 15, "color": t.INK})
    fig.update_layout(
        height=720, separators=",.", bargap=0.28,
        margin={"l": 8, "r": 80, "t": 8, "b": 8},
        uniformtext={"minsize": 12, "mode": "show"},
        plot_bgcolor="white",
    )
    st.plotly_chart(fig, width="stretch", theme="streamlit")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Nativos × Redirecionados")
        donut = pd.DataFrame({
            "Tipo": ["Nativos", "Redirecionados"],
            "Serviços": [tot["nativo"], tot["redirect"]],
        })
        fig2 = px.pie(donut, names="Tipo", values="Serviços", hole=0.55,
                      color="Tipo",
                      color_discrete_map={"Nativos": t.EXCLUSIVO, "Redirecionados": t.COMPARTILHADO})
        fig2.update_traces(textinfo="label+value+percent")
        fig2.update_layout(height=300, showlegend=False, separators=",.",
                           margin={"l": 8, "r": 8, "t": 8, "b": 8})
        st.plotly_chart(fig2, width="stretch", theme="streamlit")
