# analytics-agents marketplace

Two plugins that split self-service analytics along the only line that matters: who can
tell when an answer is wrong.

| Plugin | For | Gives them |
|---|---|---|
| **analytics-desk** | business users | ask a question, get a governed, reviewed, sourced answer |
| **analytics-workbench** | data analysts / engineers | QA analyses, author the docs the agent retrieves, run and ablate evals, migrate Genie spaces |

Built from [Anthropic's self-service analytics
post](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude) (notes:
[`../analytics-agent-notes/`](../analytics-agent-notes/index.md)). Its premise: analytics
accuracy is a **context and retrieval** problem, not a code-generation one. Skills took
measured accuracy from 21% to >95%.

## Install

```shell
/plugin marketplace add ./analytics-marketplace
/plugin install analytics-desk@analytics-agents        # business users
/plugin install analytics-workbench@analytics-agents   # data team (install both)
/reload-plugins
```

Then point them at your knowledge: create `analytics/references/INDEX.md` and one doc per
domain. [`../analytics/`](../analytics/README.md) is a filled-in example to copy the shape
from; `/analytics-workbench:new-domain <name>` bootstraps a new one.

## analytics-desk

```
skills/warehouse-knowledge   declarative: where the answer lives (the router)
skills/warehouse-runbook     procedural: clarify → route → query → review → footer
agents/sql-reviewer          hostile query review, mandatory before any number ships
commands/ask                 /analytics-desk:ask how did revenue do last month?
```

The design constraint: **the user cannot check the answer.** So the agent is routed to the
metric layer first, is not allowed to self-certify a query, and ends every answer with a
provenance footer stating source tier, freshness and owner. `raw exploration, freshness
unknown` is the signal to verify before forwarding — one of the few defences against a
wrong answer that looks fine.

Adversarial review costs ~30% more tokens and ~70% more latency for ~6% accuracy. Both
plugins assume you want that trade; if you don't, drop step 6 from the runbook and record
the delta.

## analytics-workbench

```
skills/analytics-onboarding  first run: what this is, which path, what "set up" means
skills/reference-doc         how to write and maintain docs an LLM can retrieve
skills/eval-loop             write, run, ablate, gate, harvest corrections
agents/analysis-qa           reviews a finished analysis, not just its SQL
commands/qa                  /analytics-workbench:qa <analysis>
commands/evals               /analytics-workbench:evals [id regex]
commands/new-domain          /analytics-workbench:new-domain marketing
commands/migrate-genie       /analytics-workbench:migrate-genie <space-id|file>
scripts/                     check.py, run_evals.py, migrate_genie.py (all --selftest)
hooks/                       flags a model change whose reference doc wasn't touched
```

`scripts/check.py` is the cheap CI gate: evals well-formed and actually asserting
something, every domain doc registered in the router, every link resolving, every doc
carrying the skeleton. It makes no model calls, so it runs on every PR — unlike
`run_evals.py`, which costs tokens.

### The improvement loop this is built around

```
stakeholder correction ─┐
eval failure ───────────┼─→ one-line fix in a reference doc
analysis-qa DOC GAP ────┘        ↓
                          eval case added
                                 ↓
                       re-run slice, delta in the PR
```

Every arrow is deliberately cheap. The measured failure mode is not that people write bad
docs, it's that fixing a doc costs more than ignoring it — accuracy drifted 95% → 65% in a
month without this loop.

`analysis-qa` ends every review with `DOC GAP` for exactly that reason: a finding fixed in
one analysis recurs next week; a finding written into a reference doc does not.

### Genie migration

`/analytics-workbench:migrate-genie <space-id>` exports the space, converts tables,
column synonyms, metric views, instructions, snippets and benchmarks into a reference doc
plus an eval set. It accepts a live space id, a serialized-space export, or a bundle
`databricks.yml` (following `resources.genie_spaces.<key>.file_path`, `--space` to pick
between several), and leaves `TODO` wherever Genie has no field — grain, scope,
exclusions, ownership, freshness, cross-references. Those TODOs are the migration; the
script is just the typing. Genie `sql_snippets` become metric *candidates*, never
definitions: LLM-authored metric definitions tested net-negative on evals.

Genie's `serialized_space` **v2 wraps every scalar in a list** (`"description": ["..."]`)
and spells several keys differently from the bundle examples — `text_instructions` not
`text`, `example_question_sqls` not `benchmarks`, `column_name` not `name`. The migrator
reads both, so a live API export and a hand-written bundle file produce the same output.
The selftest asserts against Databricks' documented v2 example verbatim; see
`analytics/examples/orders.serialized_space.json` for the real API shape.

## Adapting

Both plugins are portable by design — no hardcoded repo paths beyond the `analytics/`
convention, no surface-specific namespaces. The same skill should answer identically in
the IDE, in Slack, and in a scheduled job; that only holds if one repo is canonical and
everything else syncs from it.

Start with one domain, gate its launch on ~90% offline pass rate, and only then add the
next.
