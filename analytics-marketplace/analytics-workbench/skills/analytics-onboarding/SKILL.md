---
name: analytics-onboarding
version: 0.1.0
description: "IF the user is setting this analytics stack up for the first time — what is it, how do I start, how do I migrate a Genie space — THEN invoke this skill. DO NOT invoke once real domain docs exist."
---

# First run

Orient the user, then get them to one working domain. Ask which situation they're in
before giving instructions — the three paths diverge immediately.

## What this is, in two sentences

Two plugins and a folder. `analytics-desk` answers data questions with a governed source
and a provenance footer; `analytics-workbench` is how the data team writes and tests the
knowledge it answers from. The knowledge itself — reference docs and evals — lives in the
user's repo under `analytics/`, never in the plugins.

The premise worth stating once: accuracy here is a **retrieval** problem, not a SQL
problem. Nothing works until a question can be mapped to one governed table or metric.
Skills took measured accuracy from 21% to >95%.

## Which path

**A — "I have Genie spaces."** The main path.

```
/analytics-workbench:migrate-genie <space-id>
```

Converts tables, synonyms, instructions and benchmarks into a reference doc and an eval
set. Say plainly that the script does the typing and the `TODO`s are the migration — Genie
has no field for grain, exclusions, ownership, freshness or routing triggers, so those
come out unfilled by design. Then hand off to the command's own steps.

**B — "I have a warehouse, no Genie."**

```
/analytics-workbench:new-domain <name>
```

Investigates the real tables before writing anything. One domain first — not five.

**C — "I'm just looking."** Point at the reference implementation's fixture: seed it,
query `sem_orders`, ask a question, read the provenance footer. No credentials needed.

Before A or B, check `CLAUDE.md` has a filled-in connection ladder. Without it the runbook
stops at "no connection" — correctly, but the user will read it as broken.

## What "set up" means

Not "the command exited 0". A domain is ready when all four hold:

1. Its doc is registered in `analytics/references/INDEX.md` — the router is the only way
   in, and an unregistered doc is invisible no matter how good it is.
2. `python3 scripts/check.py` passes: no `TODO` tiers, every eval asserts something,
   every link resolves, the doc carries the skeleton sections.
3. Its eval slice clears ~90%.
4. For a migration: number parity passes against the old system's gold SQL
   (`run_evals.py --gold-cmd …`). Same tables is not the same answer.

Report progress as that checklist. It is the only honest measure of "done" here, and
users consistently assume step 1 is automatic.

## Explaining, when asked

- **Why a router file?** To narrow a whole warehouse to one doc before any SQL is
  written. Reading every reference doc is the failure, not thoroughness.
- **Why the provenance footer?** The person reading the answer usually cannot check it.
  The footer says how much to trust it — `raw exploration, freshness unknown` means
  verify before forwarding.
- **Why a mandatory hostile review?** ~+6% accuracy for ~+30% tokens and ~+70% latency.
  Real cost, deliberately paid; say so rather than hiding it.
- **Why evals that ignore the number?** So they don't rot when the data moves. Migrations
  are the exception — there, the old number is the promise.

## Where to go next

`reference-doc` to write the doc · `eval-loop` to test it · `warehouse-runbook` to answer
questions with it. Point at one, don't summarise all three.

Common first-run confusions, in the order they actually happen: the doc isn't in
`INDEX.md`; `CLAUDE.md` still has brackets in it; the example domain was never deleted, so
the router offers a template as if it were real.
