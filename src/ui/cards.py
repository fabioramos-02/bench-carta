"""Cards de serviço estilo portal ms.gov.br, filtráveis por perfil.

Responsabilidade única: renderizar o grid de cards (abas por perfil). Deriva a
categoria e o ícone Material a partir do prefixo da URL do serviço.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import PORTAL_BASE_URL
from src.ui import PROFILE_LABEL
from src.ui.sections import _br  # sem ciclo: sections não importa cards

_ANEXOS = Path(__file__).resolve().parents[2] / "anexos"  # ui -> src -> raiz

# prefixo do path -> (categoria legível, ícone Material Icons filled)
_CATEGORY = {
    "financas-e-impostos": ("Finanças e Impostos", "currency_exchange"),
    "saude-e-cuidado": ("Saúde e Cuidado", "local_hospital"),
    "transito-e-transportes": ("Trânsito e Transportes", "directions_car"),
    "seguranca": ("Segurança", "security"),
    "empresa-industria-e-comercio": ("Empresa, Indústria e Comércio", "business"),
    "assistencia-social": ("Assistência Social", "groups"),
    "ciencia-e-tecnologia": ("Ciência e Tecnologia", "biotech"),
}


def _category(path: str) -> tuple[str, str]:
    slug = path.strip("/").split("/", 1)[0]
    if slug in _CATEGORY:
        return _CATEGORY[slug]
    legivel = slug.replace("-", " ").replace(" e ", " e ").title()
    return legivel, "description"


def service_cards(df: pd.DataFrame) -> None:
    """Barra de perfil (estilo portal) + grid de cards (2 colunas)."""
    st.markdown("### Serviços em destaque")
    st.caption("Serviços recomendados por público alvo — mesma organização do portal.")

    # Rótulos curtos na barra (cabem sem truncar); ordem do portal
    tab_label = {
        "CIDADAO": "Cidadão",
        "SERVIDOR_PUBLICO": "Servidor Público",
        "EMPRESA": "Empresa",
        "GESTAO_PUBLICA": "Gestão Pública",
    }
    by_label = {v: k for k, v in tab_label.items()}
    chosen = st.segmented_control(
        "Perfil", list(by_label), default="Cidadão", label_visibility="collapsed"
    )
    profile = by_label.get(chosen or "Cidadão", "CIDADAO")

    # Preserva a ORDEM do portal (ordem de HIGHLIGHTED_SERVICES), sem reordenar por visitas
    subset = df[df["perfil"] == profile]
    if subset.empty:
        st.info("Sem serviços em destaque para este perfil.")
        return
    cols = st.columns(2)
    for i, (_, row) in enumerate(subset.iterrows()):
        with cols[i % 2]:
            _card(row)


# --- Área logada (gov.br): Entrar → Meu Perfil → Meus Sistemas ---------------
@lru_cache(maxsize=8)
def _img_data_uri(name: str) -> str:
    """PNG do anexo embutido como data URI (cacheado p/ não recodificar a cada rerun)."""
    b64 = base64.b64encode((_ANEXOS / name).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


_WORKSPACE_META = {
    "Meu Perfil": {
        "img": "meu perfil.png",
        "desc": "Pessoas que clicaram em <b>Entrar</b> e fizeram login com a conta gov.br.",
    },
    "Meus Sistemas": {
        "img": "meu sistemas.png",
        "desc": "Pessoas que, já logadas, abriram <b>Meus Sistemas</b> para acessar os sistemas que possuem.",
    },
}


def workspace_cards(rows: list[dict], mes: str) -> None:
    """Dois cards (imagem + pessoas + descrição) da área logada do portal."""
    by = {r["categoria"]: r for r in rows}
    c1, c2 = st.columns(2)
    for col, nome in zip((c1, c2), ("Meu Perfil", "Meus Sistemas")):
        with col:
            _workspace_card(nome, by.get(nome, {}), mes)


def _workspace_card(nome: str, row: dict, mes: str) -> None:
    meta = _WORKSPACE_META[nome]
    acessos = _br(row.get("acessos", 0))
    st.markdown(
        f"""
        <div class="ws-card" title="{acessos} visitas em {mes}">
          <img class="ws-img" src="{_img_data_uri(meta['img'])}" alt="{nome}"/>
          <div class="ws-num">{_br(row.get('pessoas', 0))}</div>
          <div class="ws-label">{nome} — pessoas</div>
          <div class="ws-desc">{meta['desc']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _card(row: pd.Series) -> None:
    categoria, icon = _category(row["path"])
    visitas = f"{int(row['visitas']):,}".replace(",", ".")
    excl = bool(row["exclusivo"])
    badge_cls = "svc-badge excl" if excl else "svc-badge"
    tipo = "Exclusivo do perfil" if excl else "Compartilhado"
    link = f"{PORTAL_BASE_URL}{row['path']}"
    st.markdown(
        f"""
        <div class="svc-card">
          <span class="svc-icon">{icon}</span>
          <div style="flex:1">
            <div class="svc-cat">{categoria}</div>
            <div class="svc-name">{row['servico']}</div>
            <div class="svc-foot">
              <span class="{badge_cls}">{visitas} visitas</span>
              <span style="font-size:.72rem;color:#6B7280">{tipo}</span>
              <a class="svc-link" href="{link}" target="_blank">abrir ↗</a>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
