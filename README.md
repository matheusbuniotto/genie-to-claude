# genie-to-claude

[![analytics](https://github.com/matheusbuniotto/genie-to-claude/actions/workflows/analytics.yml/badge.svg)](https://github.com/matheusbuniotto/genie-to-claude/actions/workflows/analytics.yml)

Move freely from Genie agents to Claude — and prove the answers survived the move.

This repo converts an existing Genie space into reference docs, skills and an eval suite
for Claude Code, plus the harness that checks Claude returns the same numbers Genie did.

## Quickstart

No Databricks account needed — steps 1–2 run offline against a seeded SQLite warehouse,
so you can watch the whole loop before pointing it at anything real.

**1. Build the fixture warehouse.** Also re-checks every numeric claim in the docs.

```bash
git clone https://github.com/matheusbuniotto/genie-to-claude && cd genie-to-claude
python3 analytics/fixtures/seed.py
```

**2. Migrate an example Genie space.** This is the real `serialized_space` v2 payload the
Databricks API returns.

```bash
uv run analytics-marketplace/analytics-workbench/scripts/migrate_genie.py \
  analytics/examples/orders.serialized_space.json --domain orders_genie
```

You get a reference doc, an eval set, and a count of the `TODO`s a human still owes —
grain, ownership, freshness and the rest that a Genie space has no field for.

**3. Install the plugins and let Claude walk you through the rest.**

```shell
/plugin marketplace add ./analytics-marketplace
/plugin install analytics-desk@analytics-agents        # business users
/plugin install analytics-workbench@analytics-agents   # data team
/reload-plugins
```

Then just ask — the `analytics-onboarding` skill picks it up from there:

> How do I set this up for my own Genie space?

**Going to production →** [`work-starter/`](work-starter/README.md) is the self-contained
copy to drop into a work repo: same plugins, empty skeleton, seven steps.

## The migration, end to end

| Step | Command | What you get |
|---|---|---|
| 1. Export | `databricks api get /api/2.0/genie/spaces/$ID?include_serialized_space=true` | the raw space |
| 2. Convert | `/analytics-workbench:migrate-genie <id>` | a reference doc + an eval set, with `TODO` wherever Genie has no field |
| 3. Close TODOs | — | grain, exclusions, ownership, freshness, routing triggers: **the actual work** |
| 4. Prove parity | `run_evals.py --gold-cmd '<warehouse CLI>'` | Genie's benchmark SQL executed, Claude's answer compared against its number |

Step 3 is the point. The migrator refuses to guess: a Genie space has no notion of grain,
scope, deprecated tables, owner or freshness, so those come out as counted `TODO`s rather
than confident fabrications. The script is the typing; the TODOs are the migration.

Step 4 is what makes it defensible. Ordinary evals grade the query and the provenance
tier — deliberately, so they don't rot when the data moves. A migration is the exception:
the old system's number is the thing you promised to preserve, so `--gold-cmd` executes
the gold SQL and asserts the agent's answer states it. A case that passes every other
assertion but fails on `numbers_ok` — right table, right tier, wrong number — is exactly
the silent failure nothing else in the suite can see.

## Why any of this shape

Built on [*How Anthropic enables self-service data analytics with
Claude*](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude)
(distilled notes: [`analytics-agent-notes/`](analytics-agent-notes/index.md)). Its
premise: **analytics accuracy is a context and retrieval problem, not a code-generation
problem.** Map the question to the right entity and the SQL is trivial. Three failure
modes account for most wrong answers, and every directory here attacks one.

| Failure mode | What addresses it |
|---|---|
| Concept ↔ entity ambiguity | one governed definition per concept (`analytics/references/metrics.md`), named segments instead of hand-rolled `WHERE` clauses |
| Retrieval failure | a thin router (`analytics/references/INDEX.md`) that narrows the warehouse to one doc before any SQL is written |
| Staleness | evals, a doc-drift hook, and a seed script that asserts the docs are still true |

Without skills, measured accuracy on analytics questions sat at 21%; with them, above 95%.
That gap is why the migration target is a skill and a doc, not a prompt.

## Layout

```
analytics-marketplace/   two installable Claude Code plugins  ← the behaviour
analytics/               reference docs, evals, fixture warehouse  ← the content
work-starter/            self-contained copy to drop into a work repo
analytics-agent-notes/   distilled notes from the source article
.github/workflows/       CI: rebuild fixture, verify doc claims, run selftests
```

The split matters: plugins ship the *procedure* and are stable; `analytics/` holds the
*knowledge*, changes daily, and lives next to the models it describes.

## The two plugins

Installed in the quickstart above. Measured with `claude plugin details`:

| Plugin | Skills | Agents | Hooks | Always-on cost |
|---|---|---|---|---|
| analytics-desk | 3 | 1 | 0 | ~334 tok |
| analytics-workbench | 7 | 1 | 1 | ~590 tok |

~920 tokens of always-on context buys the router, the runbook, both reviewers and the
first-run guide; the reference docs load on demand, which is the entire point of the
router.

**analytics-desk** — for people who can't check the answer. Routes to the semantic layer
first, spawns a hostile `sql-reviewer` before showing any number, ends every answer with a
provenance footer (source tier, freshness, owner).

**analytics-workbench** — for the people who own the data. Migrate Genie spaces, author
reference docs, QA a finished analysis, run and ablate the eval suite. Details in
[`analytics-marketplace/README.md`](analytics-marketplace/README.md).

## What makes this more than a template

- **The fixture warehouse asserts the docs are true.** Every numeric claim in
  `analytics/references/*.md` — "the hygiene filter is worth ~5% of GMV", "attributed
  revenue runs ~20% low" — is checked against seeded data on every build. Doc rot becomes
  a failing test.
- **Every gotcha is physically reproducible.** Skip the hygiene filter and GMV overstates
  by 5.1%; answer revenue from `fact_attributed_revenue` and it understates by 19.7%;
  count `user_id` and you get 666 customers instead of 400.
- **Migration output is compared before/after.**
  [`analytics/examples/migrated/`](analytics/README.md) is what the migrator produced;
  `analytics/references/orders.md` is the hand-finished version. The gap between them is
  the human work a migration needs, in full view.

## Honest status

**Verified end to end.** Both plugins install and load with every component registered.
With them installed, `orders-001` passes against the fixture: the agent routes to
`sem_orders` (tier 1), resolves "last month" to the last *complete* calendar month by
anchoring on `MAX(order_date)`, disambiguates "revenue" as net per the router, spawns
`sql-reviewer`, and closes with a full provenance footer. 194s per case — the adversarial
review is most of it, matching the ~+72% latency the article reports.

Also verified: the fixture seeds and validates every doc claim; the migrator handles all
three Genie input shapes including the real `serialized_space` v2 API schema; number
parity passes and fails correctly against the fixture on migrated gold SQL; the CI `check`
job passes. Every script has a `--selftest`.

**Skills ablation, measured small:** 4 discriminating cases, arms differing only by
`claude plugin disable/enable` — **1/4 without skills, 3/4 with**. Directionally matches
the article's 21% → >95%, but n=4 with one run per case is a direction, not a rate. The
docs alone got the agent to the right table; the skills supplied the provenance footer and
the deprecated-table routing. See
[`analytics/evals/NEGATIVE-RESULTS.md`](analytics/evals/NEGATIVE-RESULTS.md), which also
records one invalid run worth learning from.

**Known limits.** `--gold-cmd` strips three-part names so gold SQL runs against the
offline fixture and rewrites `DATE '…'` literals; it is not a dialect translator. Parity
compares numbers as written, at 0.5% tolerance, matching rates at either scale — it will
not recognise "1.2M" as 1,234,567.

## Start here

Migrating a Genie space → [`work-starter/README.md`](work-starter/README.md).
New to the ideas → [`analytics-agent-notes/index.md`](analytics-agent-notes/index.md).
Building content for your warehouse → [`analytics/README.md`](analytics/README.md).
Plugin internals → [`analytics-marketplace/README.md`](analytics-marketplace/README.md).
