# Estudo — Uso do Filtro de Perfil no Portal de Serviços MS

**Demanda:** ATA SGD/SETDIG de 27/05/2026 — "Cruzar dados do Matomo para verificar o
quanto o filtro de Perfil é utilizado no portal." Decisão a subsidiar: manter ou
remover os filtros de Órgão e Perfil.
**Autor:** Fabio Ramos · **Atualizado:** 28/05/2026 · **Status:** Fase 1 concluída.

---

## Resumo executivo
- O "filtro de Perfil" (abas *Serviços em Destaque*) é, hoje, **invisível ao Matomo**:
  trocar de aba não gera evento nem pageview.
- Só dá para medir **indiretamente**, pelos cliques em serviços **exclusivos** de cada
  perfil que partem da home.
- **Recomendação preliminar:** antes de decidir remover, instrumentar event tracking
  no clique da aba — sem isso, qualquer número é um *proxy* com viés. Os números do
  *proxy* (Fase 2) entram aqui após a extração.

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

## Fase 2 — Extração e métricas (a executar)
Rodar `python -m src.run_study` com `MATOMO_TOKEN` definido. Preencher:

| Indicador | Valor | Fonte (API) |
|---|---|---|
| Janela analisada | _(ex.: last180)_ | `config.DEFAULT_DATE` |
| Visitantes da home | ⚠️ a extrair | `VisitsSummary.get` |
| Interações atribuíveis (home→serviço exclusivo) | ⚠️ a extrair | `Transitions.getTransitionsForPageUrl` |
| **Taxa de adoção** | ⚠️ a calcular | métrica = interações ÷ visitantes |

Distribuição por perfil (Cidadão vs. Servidor — únicos atribuíveis): ⚠️ a preencher.

---

## Fase 3 — Recomendação (a consolidar pós-Fase 2)
Critério: **REMOVER** se taxa de adoção `< 2%`; **MANTER** se `≥ 2%` (limiar ajustável).

> Independente do número, registrar a recomendação metodológica: **implementar event
> tracking na troca de aba** para medir o filtro com precisão em ciclos futuros.

---

## Limitações
1. Troca de aba é invisível ao Matomo (sem event tracking).
2. Transição home→serviço é **limite superior**: inclui acessos via menu/busca, não só
   pelo card de destaque.
3. Empresa e Gestão Pública não têm serviço exclusivo → uso do filtro por esses perfis
   não é mensurável por este método.
4. Serviços compartilhados (5) ficam fora da contagem atribuível.
