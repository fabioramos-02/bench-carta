# bench-carta — Estudo de Uso do Filtro de Perfil (Portal MS)

Estudo de analytics que mede **o quanto o "filtro de Perfil"** (abas *Serviços em
Destaque*) é utilizado em `www.ms.gov.br`, para subsidiar a decisão de **manter ou
remover** os filtros de Órgão e Perfil (provocação da gestora — ATA SGD/SETDIG
27/05/2026).

## Documentos
- [`docs/plano.md`](docs/plano.md) — plano do estudo (objetivo, método, métricas).
- [`docs/estudo-uso-filtro-perfil.md`](docs/estudo-uso-filtro-perfil.md) — relatório
  (Fase 1 concluída; Fases 2–3 a preencher após rodar a extração).

## Arquitetura (SRP, módulos ≤250 linhas)
| Módulo | Responsabilidade única |
|---|---|
| `src/config.py` | Parâmetros e segredos (env). |
| `src/profiles.py` | Fonte única dos serviços por perfil (URLs reais). |
| `src/matomo/client.py` | Transporte HTTP da Reporting API. |
| `src/matomo/queries.py` | Consultas de domínio (pageviews, transitions). |
| `src/analysis/metrics.py` | Cálculo puro (adoção, distribuição, decisão). |
| `src/discovery/probe_instrumentation.py` | Fase 1 reprodutível (Playwright). |
| `src/run_study.py` | Orquestrador da Fase 2. |

## Setup
```bash
pip install -r requirements.txt
playwright install chromium          # só para a Fase 1
cp .env.example .env                 # preencher MATOMO_TOKEN
```

## Executar
```bash
# Fase 1 — descobrir o método de medição
python -m src.discovery.probe_instrumentation

# Fase 2 — extrair dados e calcular o resultado (gera data/uso-filtro-perfil.csv)
python -m src.run_study
```

## Resultado da Fase 1 (28/05/2026)
- Matomo ativo (`idSite=298`); pageview registrado em cada navegação.
- **Aba de Perfil = DOM swap puro:** clicar **não** dispara evento Matomo nem muda a
  URL → o clique de troca de aba é **invisível** ao Matomo (Método 1 e 2 descartados).
- **Serviços têm URL estruturada** (`/categoria/slug-id`) → rastreáveis por
  `Actions.getPageUrls` / `Transitions` (**Método 3 aplicável**).
- **Atribuição:** só serviços exclusivos de um perfil. Cidadão (4) e Servidor (7) são
  atribuíveis; **Empresa e Gestão Pública não têm serviço exclusivo** em destaque.

## Limitações
- Transição home→serviço é **limite superior** (inclui menu/busca, não só o card).
- Troca de aba sem clique em serviço não é mensurável sem event tracking.
