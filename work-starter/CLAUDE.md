# [project name]

Analytics agent for [team/business], built on the `analytics-desk` /
`analytics-workbench` plugins. This file is the one piece of the whole stack that's
genuinely environment-specific — fill in the brackets below and the plugins do the rest.

## Connecting to the warehouse

**Connection ladder** (the `warehouse-runbook` skill asks for this, in order):

1. Managed connection — [a configured Databricks SQL warehouse MCP server, or the
   IDE's Databricks integration, if you have one. If none, delete this line.]
2. CLI fallback — the `databricks` CLI, authenticated (`databricks auth login`).
   Default catalog: `[catalog]`. Default schema: `[schema]`.
3. Neither — ask the user to authenticate, then stop. Never fabricate a result.

Table names in the docs are real Unity Catalog three-part names
(`[catalog].[schema].[table]`) — no translation needed, unlike a local fixture.

## Semantic layer

[State which of these is true, and delete the other two:]
- We have Unity Catalog Metric Views. They are the tier-1 path — aggregate the view,
  don't reimplement its logic in raw SQL.
- We have a Genie space that serves as the semantic layer. Discover metrics/segments
  through it before writing SQL against base tables.
- We have no semantic layer yet. `analytics/references/metrics.md` documents what the
  governed metrics *would* be; until one exists, implement them as SQL against the
  tables named in the domain docs, and report `governed table` (not `semantic layer`)
  in the provenance footer.

## Knowledge lives in `analytics/`

`analytics/references/INDEX.md` is the router — read it before any query.
`analytics/evals/*.jsonl` is the offline eval suite.

## Conventions

- Reference docs and the models they describe change in the same commit.
- [If you have a staging/dev replica of the warehouse: every numeric claim in a
  reference doc should be checked against it periodically or in CI, the way
  `analytics/fixtures/seed.py` does in the reference implementation. If you don't have
  one, delete this line and rely on eval corrections instead.]
- PII / restricted columns: return the SQL for the user to run themselves, never the
  result set. [Name your restricted columns/tables here.]
