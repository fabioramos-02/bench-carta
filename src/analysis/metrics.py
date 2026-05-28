"""Cálculo das métricas do estudo. Funções puras, sem I/O.

Responsabilidade única: transformar contagens brutas em indicadores e na
decisão MANTER/REMOVER. Testável isoladamente.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config import ADOPTION_THRESHOLD, HOME_REFERRAL_FRACTION


@dataclass(frozen=True)
class StudyResult:
    home_visitors: int
    attributable_interactions: int
    proxy_rate: float  # limite superior ingênuo (visitas totais ÷ home)
    corrected_rate: float  # ajustado pela fração que vem da home
    home_fraction: float
    distribution: dict[str, float]
    per_profile_counts: dict[str, int]
    threshold: float
    recommendation: str


def adoption_rate(interactions: int, home_visitors: int) -> float:
    """Fração de visitantes da home que clicaram em serviço atribuível ao filtro."""
    if home_visitors <= 0:
        return 0.0
    return interactions / home_visitors


def profile_distribution(per_profile_counts: dict[str, int]) -> dict[str, float]:
    """Participação percentual de cada perfil sobre o total atribuível."""
    total = sum(per_profile_counts.values())
    if total <= 0:
        return {p: 0.0 for p in per_profile_counts}
    return {p: c / total for p, c in per_profile_counts.items()}


def decide(rate: float, threshold: float = ADOPTION_THRESHOLD) -> str:
    """Regra binária de decisão a partir da taxa de adoção."""
    return "MANTER" if rate >= threshold else "REMOVER"


def build_result(
    home_visitors: int,
    per_profile_counts: dict[str, int],
    threshold: float = ADOPTION_THRESHOLD,
    home_fraction: float = HOME_REFERRAL_FRACTION,
) -> StudyResult:
    """Consolida contagens por perfil no resultado final do estudo.

    `proxy_rate` é o limite superior (todas as visitas aos serviços exclusivos).
    `corrected_rate` aplica a fração empírica que realmente chega via home.
    A decisão usa a taxa corrigida.
    """
    interactions = sum(per_profile_counts.values())
    proxy = adoption_rate(interactions, home_visitors)
    corrected = proxy * home_fraction
    return StudyResult(
        home_visitors=home_visitors,
        attributable_interactions=interactions,
        proxy_rate=proxy,
        corrected_rate=corrected,
        home_fraction=home_fraction,
        distribution=profile_distribution(per_profile_counts),
        per_profile_counts=dict(per_profile_counts),
        threshold=threshold,
        recommendation=decide(corrected, threshold),
    )
