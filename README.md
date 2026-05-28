# bench-carta — Estudo de Uso do Filtro de Perfil (Portal MS)

Estudo de analytics que mede **o quanto o "filtro de Perfil"** (abas *Serviços em
Destaque*) é utilizado em `www.ms.gov.br`, para subsidiar a decisão de **manter ou
remover** os filtros de Órgão e Perfil (provocação da gestora — ATA SGD/SETDIG
27/05/2026).

> **Resultado (base 2025): recomendação REMOVER.** Uso real do filtro estimado em
> **~0,1% dos visitantes da home** — uma a duas ordens de grandeza abaixo do limiar de
> 2%. A aba *Servidor Público* é praticamente morta (366 acessos/ano).

## Documentos
- [`docs/plano.md`](docs/plano.md) — plano do estudo (objetivo, método, métricas).
- [`docs/estudo-uso-filtro-perfil.md`](docs/estudo-uso-filtro-perfil.md) — relatório
  completo (Fases 1–3 com números reais de 2025).

## Arquitetura (SRP, módulos ≤250 linhas)
| Módulo | Responsabilidade única |
|---|---|
| `src/config.py` | Parâmetros e segredos (env). |
| `src/profiles.py` | Fonte única dos serviços por perfil (URLs reais). |
| `src/matomo/client.py` | Transporte HTTP da Reporting API. |
| `src/matomo/queries.py` | Consultas de domínio (pageviews, transitions). |
| `src/analysis/metrics.py` | Cálculo puro (proxy, correção, distribuição, decisão). |
| `src/discovery/probe_instrumentation.py` | Fase 1 reprodutível (Playwright). |
| `src/run_study.py` | Orquestrador da Fase 2 (expõe `compute()` reutilizável). |
| `app.py` | Dashboard Streamlit (apresentação). |

## Setup
```bash
pip install -r requirements.txt
playwright install chromium          # só para a Fase 1
cp .env.example .env                 # preencher MATOMO_TOKEN
```

> A janela do estudo é fixada em **ano de 2025** dentro de `src/run_study.py`
> (`STUDY_WINDOW`), independente de overrides no `.env`.

## Executar
```bash
# Fase 1 — descobrir o método de medição (veredito reprodutível)
python -m src.discovery.probe_instrumentation

# Fase 2 — extrair dados e calcular (gera data/uso-filtro-perfil-2025.csv)
python -m src.run_study

# Dashboard interativo (gráficos + recomendação) — rodar da raiz do projeto
streamlit run app.py          # http://localhost:8501
# se 'streamlit' não for encontrado:
python -m streamlit run app.py
```

## Dashboard (`app.py`)
- KPIs: visitas da home, atribuíveis, proxy ingênuo e **taxa corrigida**.
- Recomendação MANTER/REMOVER em destaque.
- Gráfico de distribuição por perfil e **Top serviços** (1 barra por serviço, com o
  quantitativo rotulado em cada barra; formato pt-BR).
- Tabela detalhada com link para cada serviço no portal.
- Contraste validado em tema **claro e escuro** (paleta acessível AA).

## Resultado da Fase 1 (descoberta — 28/05/2026)
- Matomo ativo (`idSite=298`); pageview registrado em cada navegação.
- **Aba de Perfil = DOM swap puro:** clicar **não** dispara evento Matomo nem muda a
  URL → o clique de troca de aba é **invisível** ao Matomo (Métodos 1 e 2 descartados).
- **Serviços têm URL estruturada** (`/categoria/slug-id`) → rastreáveis por
  `Actions.getPageUrls` / `Transitions` (**Método 3 aplicável**).
- **Atribuição:** só serviços exclusivos de um perfil. Cidadão (4) e Servidor (7) são
  atribuíveis; **Empresa e Gestão Pública não têm serviço exclusivo** em destaque.

## Resultado das Fases 2–3 (base 2025)
| Indicador | Valor |
|---|---|
| Visitas da home | 2.316.711 |
| Visitas atribuíveis (serviços exclusivos) | 140.095 |
| Proxy ingênuo de adoção | 6,05% ⚠️ limite superior inflado |
| **Taxa corrigida** (×~1,5% via home) | **0,091%** |
| **Recomendação** | **REMOVER** (0,091% << limiar 2%) |

O proxy ingênuo é inflado por serviços de alto tráfego acessados **direto/busca**
(DEVIR 95.297, CRLV-e, CNH), não pelo filtro. Amostra de `Transitions` (dias de 2025)
mostra que só **0,95–2,47%** dos acessos a esses serviços vêm da home.

## Limitações
- Troca de aba é **invisível** ao Matomo (DOM swap, sem event tracking).
- `Transitions` por ano/mês retorna **504 Gateway Timeout** no servidor → correção via
  amostra diária extrapolada (não exata).
- Transição home→serviço é **limite superior** (inclui menu/busca, não só o card).
- Empresa e Gestão Pública não têm serviço exclusivo → não atribuíveis.
- Para número exato e auditável: instrumentar **event tracking** no clique da aba.
