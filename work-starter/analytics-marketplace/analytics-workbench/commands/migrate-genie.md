---
description: Bring a Databricks Genie space into Claude — its tables, synonyms and instructions become a reference doc and an eval set, then you fill the gaps Genie has no field for.
argument-hint: [a Genie space id, or a path to an exported yml/json]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

Migrate the Genie space **$ARGUMENTS**.

1. **Get the space.** If the argument looks like a file path, use it. Otherwise export it:

```bash
databricks api get "/api/2.0/genie/spaces/$ARGUMENTS?include_serialized_space=true" \
  > /tmp/genie-space.json
```

If the Databricks CLI isn't authenticated, stop and ask the user to run
`databricks auth login`.

2. **Convert:**

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/migrate_genie.py <file> --domain <slug>
```

Writes `analytics/references/<slug>.md` and `analytics/evals/<slug>.jsonl`, and prints
the row to add to `analytics/references/INDEX.md`. It reads both the live API's
`serialized_space` v2 (scalars wrapped in lists, `text_instructions`,
`example_question_sqls`) and the bundle spelling, so you don't need to normalise first.

3. **Close the TODOs — this is the actual work.** A Genie space has no field for routing
   triggers, grain, scope/exclusions, deprecated tables, blessed dashboards, ownership,
   freshness, or cross-references, so the migrator emits each as a `TODO` rather than
   inventing it. Work them in this order — the first two decide whether the doc is ever
   reached, the rest decide whether its answers are right:

   1. **Use For / Do NOT Use For**, then register the printed row in
      `analytics/references/INDEX.md`. An unregistered doc is invisible to the router.
   2. **Metrics (tier 1)** — Genie has no semantic layer, so a migrated doc always
      starts the agent at tier 2. Either document the metric view that covers this
      domain, or state plainly that none exists.
   3. Grain, scope/exclusions, hygiene filter, ownership, freshness — inspect the real
      table (`DESCRIBE`, row counts, date range, distinct enum values) and write what you
      verified. Ask the domain owner for what the warehouse can't tell you, ownership
      especially; the provenance footer prints it verbatim.
   4. Rewrite each migrated gotcha to name its *mechanism*, not just its rule.

4. **Promote, don't copy, the metrics.** Genie `sql_snippets` land under Query Patterns as
   *candidates*. A human moves each into the semantic layer as a governed definition, or
   deletes it. Do not treat a snippet as a metric definition.

5. **Migrated benchmarks are weak evals.** Cases from `benchmarks` get assertions derived
   from the tables in their gold SQL — that SQL was never verified, and it names tier-2
   tables because Genie had nothing else to name. Cases from `sample_questions` have no
   assertions at all and carry `expect_tier: TODO`. Strengthen both — add the hygiene
   filter, the real expected tier, and the forbidden deprecated tables — then run the
   slice with `/analytics-workbench:run-evals`.

6. **Prove parity before you switch anyone over.** Genie's gold SQL is the old system's
   answer, so run the slice with number parity on and compare like for like:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_evals.py --filter '^<slug>-' \
     --gold-cmd '<warehouse CLI reading SQL on stdin>' --keep-qualified
   ```

   Anchor each gold query to a fixed window first — "last month" gives a different number
   next month and the comparison means nothing. A case that fails on `numbers_ok` alone
   (right table, right tier, wrong number) is the finding that blocks the migration.

`scripts/check.py` fails until step 3.1 and step 5 are done (unregistered doc, `TODO`
tier, cases with no assertions). That red build is the gate, not a bug — don't silence it
by deleting the cases.

Report at the end: TODOs remaining, evals with and without assertions, and the pass rate.
The migration is done when the TODO count is zero — not when the script exits.
