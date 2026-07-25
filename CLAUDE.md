# genie-to-claude

Reference implementation of an agentic analytics stack, and the path for migrating a
Databricks Genie space into it: two Claude Code plugins plus the project content they
read. See [`analytics-marketplace/README.md`](analytics-marketplace/README.md).

## The warehouse in this repo is a fixture

There is no real warehouse here. `analytics/fixtures/warehouse.db` is a seeded SQLite
database that mirrors the tables the reference docs describe, so the eval suite runs
offline and in CI without credentials.

```bash
python3 analytics/fixtures/seed.py                      # build it (deterministic)
sqlite3 analytics/fixtures/warehouse.db "SELECT 1"      # query it
```

**Connection ladder for this repo** (the `warehouse-runbook` skill asks for this):

1. Managed connection — none configured.
2. CLI fallback — `sqlite3 analytics/fixtures/warehouse.db "<sql>"`. Use it.
3. If the file is missing, run the seed script. Never fabricate a result.

Table names in the docs are Unity Catalog three-part names (`analytics.core.fact_orders`);
in the fixture they are bare (`fact_orders`). Strip the catalog and schema when querying
it, and keep writing the full name in docs and answers — the fixture stands in for a real
warehouse, it doesn't replace the naming convention.

**The semantic layer is the `sem_orders` view** in the fixture: hygiene filter,
de-duplicated customer join and named segments baked in, documented in
`analytics/references/metrics.md`. Aggregating it is the tier-1 path — report
`semantic layer` in the provenance footer. Dropping to `fact_orders` or any other base
table is tier 2 — report `governed table`, and only do it when `sem_orders` genuinely
can't answer the question (item/category grain, attribution, marketing spend).

## Knowledge lives in `analytics/`

`analytics/references/INDEX.md` is the router — read it before any query.
`analytics/evals/*.jsonl` is the offline eval suite.

## Conventions

- Reference docs and the models they describe change in the same commit.
- Every numeric claim in a reference doc is asserted in `analytics/fixtures/seed.py`.
  Change a claim, change the assertion, or the seed fails.
- Scripts are stdlib-only or PEP-723 (`uv run`). Each has a `--selftest`.
