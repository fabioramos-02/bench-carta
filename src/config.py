"""Configuração central do estudo. Lê segredos de variáveis de ambiente.

Responsabilidade única: expor parâmetros de conexão e janelas de análise.
Nunca contém token hardcoded — `MATOMO_TOKEN` vem do ambiente / .env.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:  # carga opcional de .env em ambiente local
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dependência opcional
    pass


def _secret(key: str, default: str = "") -> str:
    """Lê um segredo: st.secrets (Streamlit Cloud) → variável de ambiente (.env).

    No Streamlit Cloud os segredos ficam em st.secrets (não em os.environ); local
    usamos .env. Tenta os dois para funcionar nos dois ambientes.
    """
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:  # sem runtime streamlit / sem secrets configurados
        pass
    return os.getenv(key, default).strip()

# --- Portal / Matomo ---------------------------------------------------------
PORTAL_BASE_URL = "https://www.ms.gov.br"
PORTAL_HOME_URL = f"{PORTAL_BASE_URL}/"
MATOMO_API_URL = "https://webanalytics.ms.gov.br/index.php"
ID_SITE = 298

# --- Funil da área logada (demanda BI) ---------------------------------------
# Jornada: Entrar (SSO gov.br) -> Área logada (/workspace) -> Meus Sistemas.
# Valores são TRECHOS de URL casados por `pageUrl=@<trecho>` (contém), NÃO URLs
# exatas: o `/workspace` tem 2 variantes de URL no Matomo e `pageUrl==` (exato)
# subconta (pegava só ~2.5k de ~9k). Ordem do dict = ordem do funil.
WORKSPACE_PAGES = {
    "Meu Perfil": "/login/callback",                        # retorno do SSO gov.br (Entrar)
    "Área logada": "/workspace",                            # entrou na área autenticada
    "Meus Sistemas": "/workspace/minha-area/meus-sistemas",  # abriu Meus Sistemas
}

# Categorias do app MS Digital (GA4) -> rótulo exato da tela (unifiedScreenName).
# "Servidor Público" é a categoria de entrada; "Contracheque" é o holerite.
MS_DIGITAL_CATEGORIAS = {
    "servidor": "Servidor Público",
    "holerite": "Contracheque",
}

# Mês alvo da consulta de acessos (YYYY-MM). Vazio => mês corrente.
# Granularidade mensal é obrigatória: o Matomo só calcula visitantes únicos em
# períodos fechados (month/year); em 'range' devolve 0.
ACESSOS_MONTH = ""

# --- Janela de análise padrão ------------------------------------------------
DEFAULT_PERIOD = "year"
DEFAULT_DATE = "2025-01-01"  # base do estudo: ano de 2025 completo

# --- Regra de decisão --------------------------------------------------------
ADOPTION_THRESHOLD = 0.02  # 2% dos visitantes da home

# Fração média das visitas a serviços que de fato vêm da home (amostra Transitions,
# dias de 2025: DEVIR 2,47% / CNH 1,53% / CRLV 0,95%). Corrige o proxy ingênuo, que
# conta acessos diretos/busca sem relação com o filtro. Ainda é limite superior
# (a home inclui menu e busca, não só o card de Perfil).
HOME_REFERRAL_FRACTION = 0.015


@dataclass(frozen=True)
class MatomoSettings:
    api_url: str
    id_site: int
    token: str
    period: str = DEFAULT_PERIOD
    date: str = DEFAULT_DATE


def load_settings() -> MatomoSettings:
    """Monta as configurações a partir do ambiente/secrets. Falha cedo sem token."""
    token = _secret("MATOMO_TOKEN")
    if not token:
        raise RuntimeError(
            "MATOMO_TOKEN ausente. Defina em st.secrets (Streamlit Cloud) ou no .env "
            "(veja .env.example)."
        )
    return MatomoSettings(
        api_url=_secret("MATOMO_API_URL") or MATOMO_API_URL,
        id_site=int(_secret("MATOMO_ID_SITE") or ID_SITE),
        token=token,
        period=_secret("MATOMO_PERIOD") or DEFAULT_PERIOD,
        date=_secret("MATOMO_DATE") or DEFAULT_DATE,
    )


# --- Google Analytics 4 (app MS Digital) -------------------------------------
@dataclass(frozen=True)
class GA4Settings:
    property_id: str
    client_id: str
    client_secret: str
    refresh_token: str


def load_ga4_settings() -> GA4Settings:
    """Configurações do GA4 a partir do ambiente. Falha cedo se faltar credencial."""
    required = {
        "GOOGLE_PROPERTY_ID": _secret("GOOGLE_PROPERTY_ID"),
        "GOOGLE_CLIENT_ID": _secret("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": _secret("GOOGLE_CLIENT_SECRET"),
        "GOOGLE_REFRESH_TOKEN": _secret("GOOGLE_REFRESH_TOKEN"),
    }
    faltando = [k for k, v in required.items() if not v]
    if faltando:
        raise RuntimeError(
            f"Credenciais GA4 ausentes: {', '.join(faltando)}. "
            "Defina em st.secrets (Streamlit Cloud) ou no .env (veja .env.example)."
        )
    return GA4Settings(
        property_id=required["GOOGLE_PROPERTY_ID"],
        client_id=required["GOOGLE_CLIENT_ID"],
        client_secret=required["GOOGLE_CLIENT_SECRET"],
        refresh_token=required["GOOGLE_REFRESH_TOKEN"],
    )
