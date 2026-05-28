"""Cards de serviço estilo portal ms.gov.br, filtráveis por perfil.

Responsabilidade única: renderizar o grid de cards (abas por perfil). Deriva a
categoria e o ícone Material a partir do prefixo da URL do serviço.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import PORTAL_BASE_URL
from src.ui import PROFILE_LABEL

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
        "SERVIDOR_PUBLICO": "Servidor",
        "EMPRESA": "Empresa",
        "GESTAO_PUBLICA": "Gestão",
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
