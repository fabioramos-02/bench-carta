"""Identidade visual institucional (Governo MS / gov DS).

Responsabilidade única: tokens de cor, injeção de CSS (fontes + classes) e o
cabeçalho institucional. Nada de dados/cálculo aqui.
"""
from __future__ import annotations

import streamlit as st

# Tokens DS-MS (Design System oficial do Estado de MS — valores exatos).
PRIMARY = "#004F9F"        # primary-500: header, CTA, links, ativo
PRIMARY_DARK = "#002F5F"   # primary-600: hover
SOFT = "#CCDCEC"           # primary-100: superfície brand soft / tags
BORDER = "#EAEBEC"         # borda de card
MUTED = "#F9F9F9"          # fundo de seções alternadas
INK = "#212A31"            # content-primary: texto principal
SECONDARY = "#6E757A"      # content-secondary: meta/placeholder
SUCCESS = "#168821"
DANGER = "#E52207"
WARNING = "#FFCD07"
# Acentos para gráficos (dentro da paleta DS): nativo = primária, redirect = secundário.
EXCLUSIVO = PRIMARY
COMPARTILHADO = SECONDARY

LOGO_URL = "https://noticias.ms.gov.br/uploads/midias/b61e2cfe41ee46169b616c9168911172.svg"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&family=Roboto:wght@400;500;700&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');

/* DS-MS: Roboto p/ corpo/UI, Open Sans p/ títulos. Base maior p/ legibilidade
   (18px — degrau DS válido mais próximo de 20). */
html {{ font-size: 18px; }}
html, body, [class*="css"] {{ font-family: 'Roboto', sans-serif; }}
h1, h2, h3, h4, h5, h6 {{ font-family: 'Open Sans', sans-serif; font-weight: 700; }}

.bi-header {{
  background: {PRIMARY};
  border-radius: 6px;
  padding: 18px 24px;
  margin-bottom: 8px;
  display: flex; align-items: center; gap: 18px;
}}
.bi-header img {{ height: 46px; }}
.bi-header .bi-title {{ color: #fff; font-weight: 700; font-size: 1.4rem; line-height: 1.15; }}
.bi-header .bi-sub {{ color: #DCEAFB; font-size: .85rem; }}

/* Barra de abas idêntica ao portal: caixa full-width, células iguais, ativa preenchida */
div[data-testid="stElementContainer"]:has(div[data-testid="stButtonGroup"]) {{ width: 100% !important; }}
div[data-testid="stButtonGroup"] div:has(> button) {{
  display: inline-flex !important; gap: 0;
  border: 0.8px solid {BORDER}; border-radius: 4px; overflow: hidden;
}}
div[data-testid="stButtonGroup"] button {{
  flex: 0 0 auto; margin: 0 !important; min-height: 0 !important;
  border: none !important; border-radius: 0 !important;
  background: #fff !important; color: {PRIMARY} !important;
  font-family: 'Open Sans', sans-serif; font-weight: 700 !important; font-size: 14px !important;
  text-transform: uppercase; letter-spacing: -.1px; padding: 15px 26px !important;
  border-right: 0.8px solid {BORDER} !important; transition: background .12s;
}}
div[data-testid="stButtonGroup"] button p {{ overflow: visible !important; text-overflow: clip !important; white-space: nowrap; }}
div[data-testid="stButtonGroup"] button:last-child {{ border-right: none !important; }}
div[data-testid="stButtonGroup"] button:hover {{ background: #F2F6FC !important; }}
div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] {{
  background: {PRIMARY} !important; color: #fff !important;
}}
div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"]:hover {{
  background: {PRIMARY_DARK} !important;
}}

/* Card idêntico ao portal */
.svc-card {{
  border: 0.8px solid {BORDER}; border-radius: 4px; background: #fff;
  padding: 18px 20px; margin-bottom: 16px; min-height: 120px;
  display: flex; gap: 16px; align-items: flex-start;
  transition: box-shadow .15s;
}}
.svc-card:hover {{ box-shadow: 0 2px 10px rgba(0,81,156,.14); }}
.svc-icon {{
  font-family: 'Material Icons'; font-size: 38px; color: {PRIMARY};
  line-height: 1; flex: 0 0 auto;
}}
.svc-cat {{ color: {PRIMARY}; font-size: .72rem; font-weight: 600; letter-spacing: .2px;
  text-transform: uppercase; line-height: 1.25; }}
.svc-name {{ color: #41464B; font-weight: 700; font-size: 1.02rem; margin: 4px 0 10px; line-height: 1.25; }}
.svc-foot {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
.svc-badge {{ background: #EAF2FC; color: {PRIMARY_DARK}; font-weight: 700; font-size: .76rem; padding: 2px 10px; border-radius: 12px; }}
.svc-badge.excl {{ background: #E4F6F3; color: #0A6E62; }}
.svc-link {{ color: {PRIMARY}; font-size: .8rem; text-decoration: none; font-weight: 600; }}
.svc-link:hover {{ text-decoration: underline; }}

/* Grade de categorias do app MS Digital — tiles estilo portal ms.gov.br.
   st.button simples só é usado nessa grade — estilo global é seguro aqui.
   Ícone em círculo soft + nome + barra azul na base do card. */
div[data-testid="stButton"] button {{
  min-height: 150px; height: 100%;
  flex-direction: column; align-items: center; justify-content: center;
  padding: 18px 12px 14px;
  border: 1px solid {BORDER}; border-radius: 8px;
  border-bottom: 3px solid {PRIMARY};
  background: #fff; text-align: center; white-space: normal;
  transition: box-shadow .15s, border-color .15s, transform .1s;
}}
div[data-testid="stButton"] button:hover {{
  border-bottom-color: {PRIMARY_DARK};
  box-shadow: 0 4px 8px rgba(0,32,64,.16);
}}
div[data-testid="stButton"] button:active {{ transform: translateY(1px); }}
/* wrappers internos do botão → empilhar ícone acima do texto, centralizado */
div[data-testid="stButton"] button > div {{ width: 100%; }}
div[data-testid="stButton"] button span[data-has-shortcut] {{
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 14px; width: 100%;
}}
div[data-testid="stButton"] button p {{
  text-align: center; line-height: 1.35; margin: 0;
  color: {PRIMARY}; font-weight: 700; font-size: .9rem;
}}
/* Ícone Material vira círculo azul-claro (idealizacao.png) */
div[data-testid="stButton"] button [data-testid="stIconMaterial"] {{
  font-size: 30px !important; color: {PRIMARY};
  background: {SOFT}; border-radius: 9999px;
  width: 60px !important; height: 60px !important; min-width: 60px;
  margin-bottom: 4px;
  display: flex; align-items: center; justify-content: center;
}}

/* Card da área logada (gov.br): imagem + pessoas + descrição */
.ws-card {{ border:0.8px solid {BORDER}; border-radius:8px; background:#fff;
  padding:18px 20px; margin-bottom:16px; min-height:230px; }}
.ws-img {{ max-height:88px; max-width:100%; border-radius:6px; margin-bottom:14px; display:block; }}
.ws-num {{ color:{PRIMARY}; font-family:'Open Sans',sans-serif; font-weight:700;
  font-size:2.2rem; line-height:1; }}
.ws-label {{ color:{INK}; font-weight:700; font-size:.95rem; margin:4px 0 8px; }}
.ws-desc {{ color:{SECONDARY}; font-size:.85rem; line-height:1.4; }}

/* Linha de serviço compacta no modal (card DS-MS enxuto) */
.svc-row {{
  display: flex; align-items: center; gap: 12px;
  border: 1px solid {BORDER}; border-radius: 8px;
  background: #fff; padding: 10px 14px; margin-bottom: 8px;
}}
.svc-row .svc-ic {{ font-family: 'Material Icons'; font-size: 22px; color: {PRIMARY}; flex: 0 0 auto; }}
.svc-row .svc-main {{ flex: 1; min-width: 0; }}
.svc-row .svc-tipo {{ color: {SECONDARY}; font-size: .68rem; font-weight: 600; text-transform: uppercase; letter-spacing: .3px; }}
.svc-row .svc-nm {{ color: {INK}; font-weight: 700; font-size: .95rem; line-height: 1.2; }}
.svc-row .svc-rt {{ display: flex; align-items: center; gap: 10px; flex: 0 0 auto; }}
.svc-row .svc-tag {{ background: {SOFT}; color: {PRIMARY_DARK}; font-weight: 700; font-size: .76rem; padding: 2px 10px; border-radius: 4px; white-space: nowrap; }}
.svc-row .svc-mt {{ color: {SECONDARY}; font-size: .74rem; white-space: nowrap; }}
.svc-row .svc-lk {{ color: {PRIMARY}; font-size: .78rem; font-weight: 600; text-decoration: none; white-space: nowrap; }}
.svc-row .svc-lk:hover {{ text-decoration: underline; }}

/* Modal (st.dialog) — largura média (~720px). width="large" do Streamlit fica
   largo demais; estreitamos sem ocupar a tela toda. */
div[data-testid="stDialog"] div[role="dialog"] {{
  width: 720px !important;
  max-width: 92vw !important;
}}

/* Legenda pessoas × acessos (rodapé do modal/seções) */
.metric-legend {{
  display: flex; gap: 18px; flex-wrap: wrap;
  border: 0.8px solid {BORDER}; border-radius: 8px; background: {MUTED};
  padding: 10px 14px; margin: 8px 0 4px;
}}
.metric-legend .ml-item {{ font-size: .82rem; color: {INK}; line-height: 1.35; }}
.metric-legend .ml-k {{ font-weight: 700; color: {PRIMARY}; }}
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
