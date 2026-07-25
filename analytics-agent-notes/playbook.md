# CHEAT CODE — Playbook de agentes de analytics/coding

> Framework de 9 passos para times implementarem agentes (Claude Code) com guidelines de qualidade, baseado nas práticas internas da Anthropic para analytics self-service.

**Fonte:** [How Anthropic enables self-service data analytics with Claude](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude) · notas locais em [`analytics-agent-notes/`](./index.md)

O problema central, segundo a Anthropic: acurácia de agente **não é problema de geração de código, é problema de contexto/retrieval**. O agente precisa mapear a pergunta do usuário para a entidade certa e atualizada no modelo de dados — depois disso a execução é trivial. Ver [`01-failure-modes.md`](01-failure-modes.md).

---

## O acrônimo

| # | Letra | Ação | Ataca qual falha | Fonte |
|---|-------|------|-------------------|-------|
| 1 | **C** | **C**anonizar os dados | Ambiguidade conceito↔entidade | [`02-data-foundations.md`](02-data-foundations.md) |
| 2 | **H** | **H**ierarquizar fontes de verdade | Ambiguidade conceito↔entidade | [`03-sources-of-truth.md`](03-sources-of-truth.md) |
| 3 | **E** | **E**nforce via tooling/CI/mandato | Obsolescência (staleness) | [`02-data-foundations.md`](02-data-foundations.md) |
| 4 | **A** | **A**rquitetar skills em pares | Falha de retrieval | [`04-skills.md`](04-skills.md) |
| 5 | **T** | **T**estar offline com evals | Todas (detecção) | [`05-validation.md`](05-validation.md) |
| 6 | **C** | **C**omparar via ablação | Todas (isolamento de causa) | [`05-validation.md`](05-validation.md) |
| 7 | **O** | **O**bservar em produção | Falha silenciosa | [`05-validation.md`](05-validation.md) |
| 8 | **D** | **D**ocumentar como código | Obsolescência (staleness) | [`04-skills.md`](04-skills.md) |
| 9 | **E** | **E**voluir com correção ativa | Todas (loop fechado) | [`05-validation.md`](05-validation.md) |

---

## 1 — Canonizar os dados

Antes de soltar um agente no warehouse, reduza o espaço de busca dele.

- Escolha **um** dataset canônico por conceito de negócio ("revenue", "usuário ativo" etc); deprecie os quase-duplicados agressivamente.
- Rollups físicos/caches devem **derivar** do modelo canônico, não viver como alternativa a ele.
- Regra prática: se o agente busca um conceito, ele deve achar **uma** resposta governada, não quarenta candidatas plausíveis.

*Fonte: [`02-data-foundations.md`](02-data-foundations.md)*

## 2 — Hierarquizar fontes de verdade

Ordem de confiança que o agente deve seguir, do mais para o menos confiável:

1. **Semantic layer** (métricas/dimensões compiladas) — primeiro recurso, sempre.
2. **Lineage / grafo de transformação** — quando a métrica não existe, decide de qual modelo agregar.
3. **Corpus de queries históricas** — não dar acesso bruto (baixo ROI); destilar em docs de referência.
4. **Contexto de negócio** (roadmaps, decisões, org) — a camada mais negligenciada; sem ela o agente responde ao que foi perguntado, não ao que foi *querido*.

⚠️ Não deixe um LLM gerar a definição da métrica sozinho — deixe o Claude gerar a *documentação*, mas o dono do dado define a métrica.

*Fonte: [`03-sources-of-truth.md`](03-sources-of-truth.md)*

## 3 — Enforce via tooling/CI/mandato

Governança sem enforcement apodrece de volta pro caos. Três frentes obrigatórias:

- **Tooling**: agente é roteado estruturalmente para o modelo canônico primeiro.
- **CI**: mudança que ignora o canônico falha o review.
- **Mandato**: time downstream constrói sobre a camada governada ou justifica por que não.

Colocalize tudo (modelagem + semantic layer + docs + dashboards) num único repo com CI que protege a integridade cross-layer.

*Fonte: [`02-data-foundations.md`](02-data-foundations.md)*

## 4 — Arquitetar skills em pares

Sem skills, acurácia ≤ 21%. Com skills, > 95%. É o item de maior alavancagem do framework inteiro.

- **Skill de conhecimento** (router fino): "tenta o semantic layer; se não cobrir, aqui estão ~30 arquivos de referência do domínio."
- **Skill de runbook** (processo): clarifica pergunta → busca fonte via skill de conhecimento → roda query → revisão adversarial → entrega com proveniência.

Use o esqueleto de doc de referência em [`04-skills.md`](04-skills.md) para cada domínio de negócio.

*Fonte: [`04-skills.md`](04-skills.md)*

## 5 — Testar offline com evals

Não solte o agente sem um conjunto de perguntas/respostas para medir gap crítico antes do usuário ver.

- Evals **dashboard-based** (comuns, gerados por Claude + validados por humano) + **long-tail** (gerados a partir de contexto de negócio).
- Toda correção de stakeholder em thread vira candidata a eval.
- Ancore o ground truth (snapshot de data, tabela fato estável) para não decair sozinho.
- Grave resultado como **telemetria** (versão da skill, SHA, modelo, pass/fail, tokens, latência) — não como log de teste descartável.
- **Gate de lançamento por domínio**: só libera para stakeholders quando a fatia de evals bate um threshold (Anthropic começou em ~90%).

*Fonte: [`05-validation.md`](05-validation.md)*

## 6 — Comparar via ablação

Toda decisão estrutural de skill é validada isolando **uma** variável de cada vez, com o eval set fixo.

- Desenhe para **resultados nulos**: o achado mais valioso da Anthropic foi negativo — dar acesso bruto (grep) a milhares de arquivos de SQL moveu a acurácia em menos de 1 ponto, mesmo com a resposta certa presente no corpus 80% das vezes. Acesso não era o gargalo; **estrutura** era.
- Ablação em granularidade de PR: todo edit relevante de skill ganha um before/after documentado na descrição do PR.
- Registre o que **não** funcionou (barato, evita repetir o experimento): mais rodadas de refinamento de doc além de certo ponto, trocar o revisor adversarial por modelo mais barato.

*Fonte: [`05-validation.md`](05-validation.md)*

## 7 — Observar em produção

- **Revisão adversarial** antes da resposta final (+6% acurácia, custo de +32% tokens / +72% latência — meça se vale o trade-off pro seu caso).
- **Rodapé de proveniência** em toda resposta: fonte (semantic layer › referência curada › tabela raw), freshness, dono do modelo.
- **Monitoramento passivo**: % de queries resolvidas via semantic layer + % de respostas corrigidas ("tabela errada", "faltou o filtro de fraude").
- Falha **silenciosa** (resposta errada, parece plausível, ninguém questiona) continua sem solução robusta — mitigue com proveniência + sign-off humano em respostas que vão pra liderança.

*Fonte: [`05-validation.md`](05-validation.md)*

## 8 — Documentar como código

Skill sem manutenção ativa fica errada em semanas (Anthropic viu acurácia cair de ~95% para ~65% em um mês).

- Skill markdown **no mesmo repo** dos modelos de transformação.
- Hook de code review que sinaliza mudança de modelo sem atualização de skill correspondente (meta: ~90% dos PRs de modelo incluem mudança de skill).
- Um canônico, sincronizado automaticamente para todas as superfícies (IDE, Slack, dashboard, MCP) — sem paths hardcoded.

*Fonte: [`04-skills.md`](04-skills.md)*

## 9 — Evoluir com correção ativa

Fecha o loop: correção de produção vira melhoria de documentação, que vira eval, que valida a próxima versão.

- Agente agendado varre canais de stakeholders por linguagem de correção, rascunha um fix de uma linha no doc de referência, abre PR pro dono do domínio.
- Caminho deliberadamente chato (editar markdown → merge → auto-sync) — baixo custo de manutenção é o que garante que aconteça de fato.
- Toda correção realimenta o conjunto de evals (passo 5).

*Fonte: [`05-validation.md`](05-validation.md)*

---

## Checklist rápido para começar

Ordem mínima recomendada ([`06-getting-started.md`](06-getting-started.md)):

- [ ] Um punhado de datasets canônicos (passo 1)
- [ ] Dezenas de evals offline (passo 5)
- [ ] Uma skill de conhecimento fina (passo 4)
- [ ] Só depois: enforcement, ablação, observabilidade, correção ativa (passos 3, 6, 7, 9)

Perguntas para alinhar com o time antes de expandir o framework: importância de acerto hoje vs. futuro, complexidade esperada do negócio, nível técnico da audiência, orçamento para acurácia extra, postura de acesso/privacidade. Detalhe em [`06-getting-started.md`](06-getting-started.md).

---

## Referências

- Artigo original: [How Anthropic enables self-service data analytics with Claude](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude)
- Notas por tópico: [`index.md`](index.md) → [`01-failure-modes.md`](01-failure-modes.md), [`02-data-foundations.md`](02-data-foundations.md), [`03-sources-of-truth.md`](03-sources-of-truth.md), [`04-skills.md`](04-skills.md), [`05-validation.md`](05-validation.md), [`06-getting-started.md`](06-getting-started.md)
