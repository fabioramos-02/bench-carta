# Estudo — Uso do Filtro de Perfil no Portal de Serviços MS

**Demanda:** ATA SGD/SETDIG de 27/05/2026 — "Cruzar dados do Matomo para verificar o
quanto o filtro de Perfil é utilizado no portal." Decisão a subsidiar: manter ou
remover os filtros de Órgão e Perfil.
**Autor:** Fabio Ramos · **Atualizado:** 28/05/2026 · **Status:** Fase 1 concluída.

---

## Resumo executivo
- **Base do estudo:** ano de **2025** completo (`period=year`, `idSite=298`).
- O "filtro de Perfil" (abas *Serviços em Destaque*) é **invisível ao Matomo**: trocar
  de aba não gera evento nem pageview. Só dá para medir por *proxy* (cliques em
  serviços exclusivos de cada perfil).
- O *proxy* ingênuo (visitas a serviços exclusivos ÷ visitas da home) dá **6,05%** —
  mas é **inflado**: esses serviços são acessados majoritariamente **direto/busca**,
  não pelo filtro. Amostra de transições mostra que só **~1–2,5%** das visitas a esses
  serviços vêm da home.
- **Estimativa corrigida do uso real do filtro: ~0,1% dos visitantes da home** — uma a
  duas ordens de grandeza **abaixo** do limiar de 2%. A aba **Servidor Público** é
  praticamente morta (**366 visitas/ano** somando todos os serviços exclusivos).
- **Recomendação:** o filtro de Perfil agrega valor desprezível ao acesso a serviços →
  **forte sinal para REMOVER** (ou redesenhar). Para um número exato e auditável,
  instrumentar *event tracking* no clique da aba antes de ciclos futuros.

---

## Fase 1 — Descoberta da instrumentação (concluída)
Executada ao vivo em `www.ms.gov.br` via Playwright (28/05/2026).

### Evidências
| Teste | Resultado |
|---|---|
| Matomo presente | ✅ `idSite=298`, `matomo.js` carregado, pageview da home registrado |
| Endpoint de tracking | `POST https://webanalytics.ms.gov.br/matomo.php?...&idsite=298` |
| Clique na aba dispara evento? | ❌ nenhuma chamada `matomo.php` nova após o clique |
| Clique na aba muda a URL? | ❌ permanece `https://www.ms.gov.br/` |
| Abas navegam para `buscar?q=`? | ❌ são troca de conteúdo client-side (DOM swap) |
| Serviços têm URL própria? | ✅ `/categoria/slug-id` (ex.: `/ciencia-e-tecnologia/conceder-acesso-ao-matomo70`) |
| Navegar ao serviço gera pageview? | ✅ `matomo.php?...&url=.../conceder-acesso-ao-matomo70` |

### Veredito do gate de método
| Método | Status | Motivo |
|---|---|---|
| 1. Event tracking | ❌ descartado | Aba não dispara evento Matomo. |
| 2. Navegação p/ busca (`buscar?q=`) | ❌ descartado | Aba é DOM swap; não navega para busca. |
| **3. Transições por serviço** | ✅ **aplicável** | Serviços têm URL estruturada e rastreável. |

> **Correção a uma premissa antiga:** a doc do repo `matomo-analytics-dashboard`
> afirma que "serviços não têm URL padronizada (ficam na raiz)". **Não é mais o caso:**
> hoje seguem `/categoria/slug-id` — isso simplifica a medição.

### Catálogo capturado e atribuição
Fonte única em `src/profiles.py`. Serviço **compartilhado** entre perfis é
**não atribuível** (não dá para saber por qual aba o usuário chegou).

| Perfil | Serviços em destaque | Exclusivos (atribuíveis) |
|---|---|---|
| Cidadão | 8 | **4** (CNH, boletim acidente, DEVIR, Mais Social) |
| Servidor Público | 8 | **7** (todos `ciencia-e-tecnologia/*`, exceto fila) |
| Empresa | 4 | **0** (tudo compartilhado) |
| Gestão Pública | 2 | **0** (tudo compartilhado) |

Compartilhados: Certidão tributária (Cidadão+Empresa+Gestão), Fila ambulatorial
(Cidadão+Servidor), CRLV-e (Cidadão+Empresa), 2ª via de conta (Cidadão+Empresa),
TVF/TA (Empresa+Gestão).

---

## Fase 2 — Extração e métricas (ano 2025)
Fonte: 1 chamada `Actions.getPageUrls` (flat, `period=year`, `date=2025-01-01`).
Saída bruta: `data/uso-filtro-perfil-2025.csv`. (`Transitions` por ano/mês retorna
**504 Gateway Timeout** no servidor — só roda em janela diária; ver amostra abaixo.)

| Indicador | Valor 2025 | Fonte (API) |
|---|---|---|
| Janela analisada | ano 2025 (`year` / `2025-01-01`) | `Actions.getPageUrls` |
| Visitas da home (`/`) | **2.316.711** | `Actions.getPageUrls` |
| Visitas a serviços exclusivos (proxy ingênuo) | **140.095** | idem |
| **Proxy ingênuo de adoção** | **6,05%** ⚠️ limite superior inflado | 140.095 ÷ 2.316.711 |

### Distribuição entre perfis atribuíveis (proxy ingênuo)
| Perfil | Visitas (exclusivos) | Participação |
|---|---|---|
| Cidadão | 139.729 | **99,7%** |
| Servidor Público | 366 | 0,3% |
| Empresa / Gestão | — | não atribuível (sem serviço exclusivo) |

Cidadão é dominado por serviços de alto tráfego acessados **direto**, não pelo filtro:
DEVIR **95.297**, CNH **19.284**, Boletim de acidente **17.826**, Mais Social **7.322**.

### Correção: quanto vem REALMENTE da home (amostra de Transitions, dias de 2025)
| Serviço | pageviews (4 dias) | refs da home | % home |
|---|---|---|---|
| DEVIR | 2.674 | 66 | **2,47%** |
| CNH | 392 | 6 | **1,53%** |
| CRLV-e | 4.533 | 43 | **0,95%** |

Aplicando ~1,5% (fração média vinda da home) ao volume anual atribuível:
`140.095 × 0,015 ≈ 2.100 visitas/ano` chegando via home → **~0,09% dos visitantes da
home**. E mesmo essas incluem menu e busca da home, não só o card de Perfil → o uso do
filtro é **ainda menor**.

---

## Fase 3 — Recomendação
Critério: **REMOVER** se taxa de adoção `< 2%`; **MANTER** se `≥ 2%`.

- Proxy ingênuo (6,05%) **não** serve de base: conta tráfego direto que nada tem a ver
  com o filtro.
- Métrica corrigida (**~0,1%**) está **muito abaixo** do limiar → **recomendação:
  REMOVER** o filtro de Perfil (ou substituí-lo por categorias/busca, alinhado à
  Proposta 2 de reorganização).
- A aba **Servidor Público** é injustificável: 366 acessos/ano a serviços internos da
  SETDIG num portal com 2,3M de visitas na home.
- **Ressalva metodológica:** para um número exato e auditável (sem extrapolação de
  amostra), instrumentar *event tracking* no clique da aba. Mas a evidência atual já é
  suficiente para indicar uso desprezível.

---

## Limitações
1. Troca de aba é invisível ao Matomo (sem event tracking).
2. Transição home→serviço é **limite superior**: inclui acessos via menu/busca, não só
   pelo card de destaque.
3. Empresa e Gestão Pública não têm serviço exclusivo → uso do filtro por esses perfis
   não é mensurável por este método.
4. Serviços compartilhados (5) ficam fora da contagem atribuível.
