# Sobre o projeto — BI de Acessos do Portal Único e do App MS Digital

> Documento de projeto (gestão + memória técnica). Governo de MS · SETDIG.
> Repositório: `bench-carta`. Dashboard de produção: https://setdig-dados.streamlit.app/
> Base de dados deste documento: **mês 05/2026**.

## 1. Por que este levantamento

A provocação partiu da gestão (ATA SGD/SETDIG de 27/05/2026): **medir o uso real dos
recursos do Portal Único** (https://www.ms.gov.br) para decidir, com evidência,
se o **Filtro de Perfil** (Cidadão / Servidor / Empresa / Gestão Pública) deve ser
**mantido ou removido**. Em paralelo, a gestão quer enxergar **como o cidadão usa o app
MS Digital** — quais categorias e serviços concentram acesso, e quanto do app ainda só
redireciona para outros sites.

O princípio é a **Lei 13.460** (foco no cidadão): só faz sentido manter um componente
se ele de fato ajuda o cidadão a chegar ao serviço. Decisão de produto baseada em dado,
não em achismo.

## 2. O que o repositório coleta

Duas fontes, dois painéis no dashboard:

| Painel                        | Fonte                | O que mede                                    | Métrica "pessoas"                    | Métrica "acessos"               |
| ----------------------------- | -------------------- | --------------------------------------------- | ------------------------------------ | ------------------------------- |
| **Portal Único**              | Matomo (idSite 298)  | Uso do Filtro de Perfil; funil da área logada | `nb_uniq_visitors` (visitante único) | `nb_visits` (visitas)           |
| **MS Digital APP** — nativo   | GA4 (tela do app)    | Serviços que são telas do app                 | `activeUsers`                        | `screenPageViews`               |
| **MS Digital APP** — redirect | GA4 (evento `click`) | Serviços que abrem site externo               | `totalUsers`                         | `eventCount` (rótulo "cliques") |

O total de uma **categoria** do app **não é soma** dos serviços: vem em cascata
(`pessoas_fonte`) — tela da categoria → senão clique direto → senão o maior serviço.

## 3. Indicadores acompanhados

1. **Taxa de adoção do Filtro de Perfil** — uso real ÷ visitantes da home.
2. **Funil da área logada (gov.br)** — Entrar → Área logada → Meus Sistemas.
3. **Pessoas por categoria do app** — ranking de procura do cidadão.
4. **Nativo × Redirecionado** — quanto do app entrega tela própria vs só encaminha.

## 4. Storytelling dos dados (mês 05/2026)

**Filtro de Perfil — uso baixíssimo.** Dos **158.166** visitantes da home, o uso real do
filtro é **0,101%** — cerca de **1 a cada 990 pessoas**.

**Área logada — funil que decai a cada passo.** No mês, **46.275** pessoas fizeram login
via gov.br; **9.137** entraram na área logada (`/workspace`); **5.870** abriram
**Meus Sistemas**. De cada login, ~1 em 8 chega aos sistemas. O grande volume está na
porta de entrada (login), não no consumo da área logada.

**App MS Digital — concentração e redirecionamento.** O app tem **111 serviços** em
**20 categorias**, mas **71 (64%)** apenas **redirecionam** para outros sites — ~6 de
cada 10. O que o cidadão mais procura: **Saúde (10.775)**, **Servidor Público (9.227)**
e **Educação (5.533)** pessoas. Trazer serviços redirecionados para dentro do app
melhora a experiência e permite medir melhor o uso.

## 5. Validação dos dados do modal (auditoria — "os números batem?")

Pergunta: na categoria **Saúde**, o cabeçalho mostra **10.775 pessoas**, mas a soma das
pessoas dos serviços dá **24.117**. Está errado?

**Veredito: os dados estão consistentes.** Não é soma — é contagem de **únicos**:

| Medida                                               | Valor              |
| ---------------------------------------------------- | ------------------ |
| Maior serviço (Cartão SUS Online)                    | 8.242 pessoas      |
| **Total da categoria** (tela "Saúde", `activeUsers`) | **10.775 pessoas** |
| Soma das pessoas dos 11 serviços                     | 24.117 pessoas     |

O total (10.775) cai **entre** o maior serviço (8.242) e a soma (24.117) — exatamente a
assinatura de uma contagem **desduplicada**. `activeUsers` (GA4) conta cada pessoa **1×
por escopo**: quem abre Cartão SUS **e** Vacinação conta nos dois serviços, mas **1× na
categoria**. Por isso a soma dos serviços é maior que o total da categoria. Esperado,
não bug.

## 6. Glossário — pessoas × acessos (para a gestão)

- **Pessoas** = usuários **únicos** no período. Cada cidadão conta **1 vez**, mesmo que
  acesse várias vezes. É o "quantas pessoas diferentes".
- **Acessos / Cliques** = total de **aberturas**. Uma mesma pessoa pode contar **várias
  vezes**. É o "quantas vezes foi aberto" (volume).
- **Por que pessoas não somam:** únicos são desduplicados por escopo. Somar pessoas de
  serviços diferentes conta a mesma pessoa mais de uma vez → sempre dá mais que o real.
  Use o total da categoria para "quantas pessoas", e a soma só para volume relativo.

| Termo técnico                     | Fonte        | Significa                                   |
| --------------------------------- | ------------ | ------------------------------------------- |
| `nb_uniq_visitors` / `nb_visits`  | Matomo       | pessoas únicas / visitas (portal)           |
| `activeUsers` / `screenPageViews` | GA4 (tela)   | pessoas únicas / visualizações (app nativo) |
| `totalUsers` / `eventCount`       | GA4 (clique) | pessoas / cliques (app redirect)            |

## 7. Limitações e nível de confiança

- **Matomo só calcula único em período fechado** (dia/semana/mês/ano); em intervalo
  livre o único vem zerado — por isso o funil usa o mês.
- **Funil ≈ aproximado:** os degraus são uniques por página, não cohort fechada — alguém
  pode abrir Meus Sistemas via favorito sem passar pela home logada na mesma visita.
- **Taxa de adoção do filtro** é estimada (a home inclui menu e busca, não só o card de
  Perfil) — é limite superior, não medida exata.
- **Serviços redirecionados** medem clique (intenção de sair), não a conclusão no destino.

---

Relacionado: estudo de método em `docs/estudo-uso-filtro-perfil.md` · prompt do estudo no
vault (`30-ia/prompts/2026-05-28-estudo-matomo-uso-filtro-perfil.md`).
