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

# --- Portal / Matomo ---------------------------------------------------------
PORTAL_BASE_URL = "https://www.ms.gov.br"
PORTAL_HOME_URL = f"{PORTAL_BASE_URL}/"
MATOMO_API_URL = "https://webanalytics.ms.gov.br/index.php"
ID_SITE = 298

# --- Janela de análise padrão ------------------------------------------------
DEFAULT_PERIOD = "year"
DEFAULT_DATE = "2025-01-01"  # base do estudo: ano de 2025 completo

# --- Regra de decisão --------------------------------------------------------
ADOPTION_THRESHOLD = 0.02  # 2% dos visitantes da home


@dataclass(frozen=True)
class MatomoSettings:
    api_url: str
    id_site: int
    token: str
    period: str = DEFAULT_PERIOD
    date: str = DEFAULT_DATE


def load_settings() -> MatomoSettings:
    """Monta as configurações a partir do ambiente. Falha cedo se faltar token."""
    token = os.getenv("MATOMO_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "MATOMO_TOKEN ausente. Defina a variável de ambiente ou crie um .env "
            "(veja .env.example)."
        )
    return MatomoSettings(
        api_url=os.getenv("MATOMO_API_URL", MATOMO_API_URL),
        id_site=int(os.getenv("MATOMO_ID_SITE", ID_SITE)),
        token=token,
        period=os.getenv("MATOMO_PERIOD", DEFAULT_PERIOD),
        date=os.getenv("MATOMO_DATE", DEFAULT_DATE),
    )
