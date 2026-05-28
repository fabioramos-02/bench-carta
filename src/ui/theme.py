"""Identidade visual institucional (Governo MS / gov DS).

Responsabilidade única: tokens de cor, injeção de CSS (fontes + classes) e o
cabeçalho institucional. Nada de dados/cálculo aqui.
"""
from __future__ import annotations

import streamlit as st

# Tokens (gov MS + feedback gov.br)
PRIMARY = "#004F9F"
PRIMARY_DARK = "#003B75"
SUCCESS = "#168821"
DANGER = "#E52207"
WARNING = "#FFCD07"
EXCLUSIVO = "#0E9F8E"
COMPARTILHADO = "#9AA0A6"
INK = "#1B1B1B"

LOGO_URL = "https://noticias.ms.gov.br/uploads/midias/b61e2cfe41ee46169b616c9168911172.svg"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Raleway:wght@400;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');

html, body, [class*="css"] {{ font-family: 'Raleway', sans-serif; }}

.bi-header {{
  background: {PRIMARY};
  border-radius: 10px;
  padding: 18px 24px;
  margin-bottom: 8px;
  display: flex; align-items: center; gap: 18px;
}}
.bi-header img {{ height: 46px; }}
.bi-header .bi-title {{ color: #fff; font-weight: 800; font-size: 1.45rem; line-height: 1.15; }}
.bi-header .bi-sub {{ color: #DCEAFB; font-size: .85rem; }}

.svc-card {{
  border: 1px solid #E0E6ED; border-radius: 10px; background: #fff;
  padding: 16px 18px; margin-bottom: 14px; min-height: 118px;
  display: flex; gap: 14px; box-shadow: 0 1px 3px rgba(0,0,0,.06);
  transition: box-shadow .15s, border-color .15s;
}}
.svc-card:hover {{ box-shadow: 0 4px 14px rgba(0,79,159,.18); border-color: {PRIMARY}; }}
.svc-icon {{
  font-family: 'Material Symbols Outlined'; font-size: 34px; color: {PRIMARY};
  line-height: 1; flex: 0 0 auto;
}}
.svc-cat {{ color: {PRIMARY}; font-size: .68rem; font-weight: 700; letter-spacing: .4px; text-transform: uppercase; }}
.svc-name {{ color: #2B2B2B; font-weight: 700; font-size: 1rem; margin: 2px 0 8px; }}
.svc-foot {{ display: flex; align-items: center; gap: 10px; }}
.svc-badge {{ background: #EAF2FC; color: {PRIMARY_DARK}; font-weight: 700; font-size: .78rem; padding: 2px 10px; border-radius: 12px; }}
.svc-badge.excl {{ background: #E4F6F3; color: #0A6E62; }}
.svc-link {{ color: {PRIMARY}; font-size: .8rem; text-decoration: none; font-weight: 600; }}
.svc-link:hover {{ text-decoration: underline; }}
</style>
"""


def inject_css() -> None:
    """Injeta fontes (Raleway + Material Symbols) e classes de componente."""
    st.markdown(_CSS, unsafe_allow_html=True)


def header(title: str, subtitle: str) -> None:
    """Cabeçalho institucional: barra #004F9F com logo MS + título."""
    st.markdown(
        f"""
        <div class="bi-header">
          <img src="{LOGO_URL}" alt="Governo MS"
               onerror="this.style.display='none'"/>
          <div>
            <div class="bi-title">{title}</div>
            <div class="bi-sub">{subtitle}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
