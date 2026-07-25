# `analytics/` — the project side of the analytics agent

Everything here is **project-owned content**, not plugin code. It changes daily and lives
in the repo next to the models it describes. The behaviour that reads it ships in
[`../analytics-marketplace/`](../analytics-marketplace/README.md).

```
references/INDEX.md          the router: domain map + terms that must be disambiguated
references/*.md              one doc per business domain (grain, hygiene filter, gotchas)
evals/*.jsonl                offline evals, graded on the query and the tier, not the number
evals/results.jsonl          appended by every eval run — telemetry, load it into a table
evals/NEGATIVE-RESULTS.md    ablations that came back flat, so nobody re-runs them
fixtures/seed.py             builds a local SQLite warehouse; asserts the docs are true
examples/                    sample Genie spaces and what the migrator makes of them
```

This directory is a worked example (a fictional marketplace: orders, revenue, refunds)
of the stack described in [Anthropic's self-service analytics
post](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude) — notes in
[`../analytics-agent-notes/`](../analytics-agent-notes/index.md). Copy the shape, replace
the content.

## Why the files are shaped this way

| Failure mode | What addresses it |
|---|---|
| Concept ↔ entity ambiguity | `references/metrics.md` — one governed definition per concept, named segments instead of hand-rolled `WHERE` clauses |
| Retrieval failure | `references/INDEX.md` — the router narrows the warehouse to one doc before any SQL is written |
| Staleness | `evals/` + the doc-drift hook — the PR that changes a model changes its doc, and evals catch what slips |

Two domains are documented, which is the minimum that makes a router worth having:

- **`orders.md`** — the skeleton filled in properly: grain, hygiene filter with the cost
  of omitting it, cross-table naming drift, gotchas that name their mechanism.
- **`marketing.md`** — the *routing trigger* case. Attributed revenue is ~20% below total
  revenue by construction, so the doc's job is as much to send "how much revenue did we
  make" back to `orders.md` as it is to answer its own questions.

`INDEX.md` also names the domains that are **not** documented. An undocumented question
gets "that domain isn't documented", not an answer improvised from a neighbouring table.

## Evals

19 cases across `evals/orders.jsonl` and `evals/marketing.jsonl`, including two that must
*escalate* rather than answer (a PII request, an undocumented domain) and one that must
route across domains. Assertions are on tables, filters, metric names and the provenance
tier — never on numbers, which move daily.

```bash
python3 fixtures/seed.py                                                   # from analytics/
cd .. && python3 analytics-marketplace/analytics-workbench/scripts/run_evals.py
```

With the workbench plugin installed, `/analytics-workbench:evals` does the same and
interprets the failures.

## The fixture warehouse

`fixtures/seed.py` builds `fixtures/warehouse.db` — a deterministic SQLite database with
the tables the docs describe, so the suite runs offline and in CI with no credentials.
It does two things:

1. Gives the agent something real to query. Every gotcha in the docs is present in the
   rows, so ignoring one produces a visibly wrong number: skipping the hygiene filter
   overstates GMV by 5.1%, answering revenue from `fact_attributed_revenue` understates
   it by 19.7%, counting `user_id` reports 666 customers instead of 400, and a naive
   `dim_customer` join inflates revenue by 66%.
2. **Asserts the reference docs are true.** Every numeric claim in `references/*.md` is
   checked against the data. Change a doc's percentage without changing the warehouse and
   the seed script fails — which is the documentation rot the whole system exists to
   catch, turned into an assertion.

The `.db` is generated and gitignored. Rebuild it any time; the row data is identical
across runs.

## Genie migration example

Three input shapes, same pipeline:

- `examples/orders.serialized_space.json` — **the real thing**, Genie `serialized_space`
  v2 as `databricks api get` returns it: every scalar wrapped in a list,
  `text_instructions`, `example_question_sqls`, `column_name`.
- `examples/orders.genie_space.yml` — the hand-written bundle spelling.
- `examples/databricks.yml` — an Asset Bundle pointing at the above via `file_path`.

`examples/migrated/` is what the migrator produced —
useful as a before/after: descriptions, synonyms, instructions and benchmarks carry over,
while the routing trigger, tier-1 metric coverage, grain, exclusions, deprecated tables,
blessed dashboards, ownership, freshness and cross-references come out as `TODO` because
Genie has no field for them.

```bash
M=../analytics-marketplace/analytics-workbench/scripts/migrate_genie.py
uv run $M examples/orders.genie_space.yml --domain orders_genie \
  --out examples/migrated/references --evals-out examples/migrated/evals
uv run $M examples/databricks.yml --space orders_space --domain orders_genie   # identical
```

Compare `examples/migrated/references/orders_genie.md` against the hand-finished
`references/orders.md`: the gap between them is exactly the human work a migration needs.

### Number parity

The migrated cases carry Genie's benchmark SQL as `gold_sql` — the old system's answer.
Run the slice with parity on and the gold query is executed against the fixture, with the
agent's answer checked against the number it returned:

```bash
cd .. && python3 analytics-marketplace/analytics-workbench/scripts/run_evals.py \
  analytics/examples/migrated/evals/orders_genie.jsonl \
  --gold-cmd 'sqlite3 analytics/fixtures/warehouse.db'
```

`orders_genie-001` resolves to 195,125.93 against the fixture. An answer that cites
`fact_orders`, applies the hygiene filter and reports 210,400 passes every other
assertion and fails on `numbers_ok` — which is the whole reason this mode exists.

## Where to point it

The plugins expect `analytics/references/` and `analytics/evals/` at the repo root. Using
different paths is fine — say so in `CLAUDE.md` and the router will follow.
