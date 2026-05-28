"""Fonte única de verdade dos serviços em destaque por perfil.

Dados capturados ao vivo em www.ms.gov.br na Fase 1 (descoberta) — 28/05/2026.
As URLs são reais e estruturadas (`/categoria/slug-id`), confirmando rastreio
direto por `Actions.getPageUrls`.

Responsabilidade única: descrever o catálogo de destaque e derivar quais
serviços são exclusivos de um perfil (atribuíveis) vs. compartilhados (ambíguos).
"""
from __future__ import annotations

from collections import Counter

# perfil -> { rótulo do serviço: caminho relativo no portal }
HIGHLIGHTED_SERVICES: dict[str, dict[str, str]] = {
    "CIDADAO": {
        "Certidão tributária estadual": "/financas-e-impostos/certidao-tributaria-estadual-emissao-certidao-circunstanciada-de-debitos-estaduais174",
        "Consultar Fila ambulatorial": "/saude-e-cuidado/consultar-fila-ambulatorial118",
        "Emitir CRLV-e (licenciamento digital)": "/transito-e-transportes/emissao-de-crlv-e-licenciamento-digital13",
        "Emissão da CNH": "/transito-e-transportes/emissao-da-carteira-nacional-de-habilitacao174",
        "Boletim on-line de acidente sem vítimas": "/seguranca/051-boletim-on-line-de-acidente-de-transito-atendimento-sem-vitimas170",
        "Delegacia Virtual (DEVIR)": "/seguranca/delegacia-virtual-devir105",
        "2ª via de conta de água/esgoto": "/empresa-industria-e-comercio/solicitar-emissao-de-2a-via-de-conta-de-agua-e-esgoto113",
        "Inclusão no Programa Mais Social": "/assistencia-social/solicitacao-de-inclusao-no-programa-mais-social118",
    },
    "SERVIDOR_PUBLICO": {
        "Conceder acesso ao Matomo": "/ciencia-e-tecnologia/conceder-acesso-ao-matomo70",
        "Consultar Fila ambulatorial": "/saude-e-cuidado/consultar-fila-ambulatorial118",
        "Solicitar acesso ao Grafana": "/ciencia-e-tecnologia/solicitar-acesso-ao-grafana21",
        "Primeiro acesso aos canais institucionais": "/ciencia-e-tecnologia/solicitar-primeiro-acesso-aos-canais-institucionais-oficiais9",
        "Aumento de quota de e-mail oficial": "/ciencia-e-tecnologia/solicitar-aumento-de-quota-de-e-mail-oficial87",
        "Liberação/bloqueio de acesso à internet": "/ciencia-e-tecnologia/solicitar-liberacao-ou-bloqueio-de-acesso-a-conteudo-da-internet93",
        "Acesso aos sistemas institucionais SETDIG": "/ciencia-e-tecnologia/solicitar-acesso-aos-sistemas-institucionais-mantidos-pela-setdig91",
        "Treinamento do WordPress": "/ciencia-e-tecnologia/solicitar-treinamento-do-wordpress70",
    },
    "EMPRESA": {
        "Certidão tributária estadual": "/financas-e-impostos/certidao-tributaria-estadual-emissao-certidao-circunstanciada-de-debitos-estaduais174",
        "Emitir CRLV-e (licenciamento digital)": "/transito-e-transportes/emissao-de-crlv-e-licenciamento-digital13",
        "2ª via de conta de água/esgoto": "/empresa-industria-e-comercio/solicitar-emissao-de-2a-via-de-conta-de-agua-e-esgoto113",
        "Termo de Verificação Fiscal (TVF)/Apreensão (TA)": "/financas-e-impostos/termo-de-verificacao-fiscal-tvf-ou-termo-de-apreensao-ta-baixa-ou-alteracao99",
    },
    "GESTAO_PUBLICA": {
        "Certidão tributária estadual": "/financas-e-impostos/certidao-tributaria-estadual-emissao-certidao-circunstanciada-de-debitos-estaduais174",
        "Termo de Verificação Fiscal (TVF)/Apreensão (TA)": "/financas-e-impostos/termo-de-verificacao-fiscal-tvf-ou-termo-de-apreensao-ta-baixa-ou-alteracao99",
    },
}


def all_paths() -> set[str]:
    """Todos os caminhos de serviço em destaque (sem repetição)."""
    return {path for svc in HIGHLIGHTED_SERVICES.values() for path in svc.values()}


def _path_frequency() -> Counter:
    counter: Counter = Counter()
    for services in HIGHLIGHTED_SERVICES.values():
        counter.update(set(services.values()))
    return counter


def unique_services() -> dict[str, dict[str, str]]:
    """Serviços exclusivos de UM perfil — base atribuível da medição."""
    freq = _path_frequency()
    return {
        profile: {label: path for label, path in services.items() if freq[path] == 1}
        for profile, services in HIGHLIGHTED_SERVICES.items()
    }


def shared_services() -> set[str]:
    """Caminhos presentes em 2+ perfis — não atribuíveis a um perfil único."""
    return {path for path, n in _path_frequency().items() if n > 1}


def attributable_profiles() -> list[str]:
    """Perfis que possuem ao menos um serviço exclusivo em destaque."""
    return [p for p, svc in unique_services().items() if svc]
