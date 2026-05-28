"""Cards de serviço estilo portal ms.gov.br, filtráveis por perfil.

Responsabilidade única: renderizar o grid de cards (abas por perfil). Deriva a
categoria e o ícone Material a partir do prefixo da URL do serviço.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import PORTAL_BASE_URL
from src.ui import PROFILE_LABEL

# prefixo do path -> (categoria legível, ícone Material Symbols)
_CATEGORY = {
    "financas-e-impostos": ("Finanças e Impostos", "request_quote"),
    "saude-e-cuidado": ("Saúde e Cuidado", "medical_services"),
    "transito-e-transportes": ("Trânsito e Transportes", "directions_car"),
    "seguranca": ("Segurança", "shield"),
    "empresa-industria-e-comercio": ("Empresa, Indústria e Comércio", "apartment"),
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
    """Abas por perfil + grid de cards (2 colunas) estilo portal."""
    st.subheader("Serviços em destaque por perfil")
    st.caption("Mesma organização do portal: escolha o perfil para ver seus serviços.")

    profiles = list(PROFILE_LABEL)
    tabs = st.tabs([PROFILE_LABEL[p] for p in profiles])
    for tab, profile in zip(tabs, profiles):
        with tab:
            subset = df[df["perfil"] == profile].sort_values("visitas", ascending=False)
            if subset.empty:
                st.info("Sem serviços em destaque para este perfil.")
                continue
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
