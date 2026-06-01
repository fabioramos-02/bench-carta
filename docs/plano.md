# Estudo Matomo — Uso do "Filtro de Perfil" no Portal Único

> Decisão a subsidiar: **manter ou remover** os filtros de Órgão e Perfil
> (provocação da gestora Duda — ATA SGD/SETDIG de 27/05/2026).

## 1. Objetivo
Quantificar o quanto o "filtro de Perfil" (abas **Serviços em Destaque**:
CIDADÃO / SERVIDOR PÚBLICO / EMPRESA / GESTÃO PÚBLICA) é utilizado no portal
`www.ms.gov.br` e emitir recomendação binária (MANTER / REMOVER) com evidência
numérica rastreável.

## 2. Contexto técnico
- Matomo `idSite=298`, API `https://webanalytics.ms.gov.br`.
- "Filtro de Perfil" = bloco **Serviços em Destaque → "Serviços recomendados por
  público alvo"**, com 4 abas.
- Token em variável de ambiente `MATOMO_TOKEN` (nunca hardcodar).

## 3. Estratégia — gate de método (3 níveis, mais preciso → mais fraco)
1. **Event tracking** — clicar a aba dispara evento Matomo (`e_c/e_a/e_n`)?
   Se sim, medir via `Events.get*`. ✅ preciso.
2. **Navegação para busca** — clicar a aba/serviço navega para `buscar?q=<Perfil>`?
   Se sim, medir via `Actions.getSiteSearchKeywords`. ⚠️ proxy.
3. **Transições por serviço (fallback)** — `Transitions.getTransitionsForPageUrl`
   para cada serviço em destaque, contando entradas vindas da home. Atribuir perfil
   SOMENTE a serviços exclusivos de um perfil. ⚠️ mais fraco; explicitar limite.

> **Resultado da Fase 1 (descoberta) — ver `docs/estudo-uso-filtro-perfil.md`:**
> Método 1 e 2 **descartados** por evidência ao vivo. Método aplicável = **3**,
> reforçado: serviços têm **URL estruturada** (`/categoria/slug-id`), então cada
> serviço é rastreável por `Actions.getPageUrls`.

## 4. Fases
- **Fase 1 — Descoberta (Playwright):** classificar o método. ✅ concluída.
- **Fase 2 — Extração e métricas (API Matomo):** taxa de adoção + distribuição por
  perfil + conversão por serviço atribuível.
- **Fase 3 — Recomendação:** aplicar critério numérico e escrever relatório.

## 5. Métricas
- **Taxa de adoção** = interações atribuíveis ao filtro ÷ visitantes da home, no período.
- **Distribuição por perfil** = % de cliques em serviços exclusivos de cada perfil.
- **Janela padrão:** últimos 6 meses fechados (ampliar p/ 12 se baixo volume).

## 6. Critério de decisão
- **REMOVER** se taxa de adoção `< 2%` dos visitantes da home.
- **MANTER** se `≥ 2%`.
- Limiar ajustável e justificado no relatório.

## 7. Limitações conhecidas
- Aba é DOM swap puro → o clique de troca de aba é **invisível** ao Matomo.
- Transição home→serviço inclui acessos via menu/busca, não só via card de destaque
  → métrica é **limite superior**.
- Serviços compartilhados entre perfis são **não atribuíveis**; Empresa e Gestão
  Pública não possuem serviços exclusivos em destaque.

## 8. Estrutura do repositório
```
bench-carta/
├── docs/
│   ├── plano.md
│   └── estudo-uso-filtro-perfil.md     # relatório (Fase 1 preenchida)
├── src/
│   ├── config.py                       # env, idSite, base URLs
│   ├── profiles.py                     # fonte única: serviços por perfil (URLs reais)
│   ├── matomo/
│   │   ├── client.py                   # transporte HTTP (Reporting API)
│   │   └── queries.py                  # consultas de domínio (pageviews, transitions)
│   ├── analysis/
│   │   └── metrics.py                  # funções puras: adoção, distribuição, decisão
│   ├── discovery/
│   │   └── probe_instrumentation.py    # Fase 1 reprodutível (Playwright)
│   └── run_study.py                    # orquestrador Fase 2
├── data/                               # saídas CSV
├── anexos/                             # screenshots dos perfis
├── requirements.txt
└── .env.example
```

## 9. Ferramentas
- Playwright (Python) — descoberta.
- API Matomo Reporting: `Actions.getPageUrls`, `Transitions.getTransitionsForPageUrl`,
  `VisitsSummary.get` (visitantes da home).
- pandas / plotly — processamento e visualização.
