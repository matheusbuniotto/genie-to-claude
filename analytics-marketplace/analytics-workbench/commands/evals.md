---
description: Run the offline eval suite (or one slice) and report pass rate, failures, and what to fix.
argument-hint: [optional id regex, e.g. ^orders- ]
allowed-tools: Bash, Read, Edit, Glob, Grep
---

Run the offline evals. Follow the `eval-loop` skill.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_evals.py ${ARGUMENTS:+--filter "$ARGUMENTS"}
```

On a migrated slice, add number parity — the gold SQL came from the system being
replaced, so this is the run that says whether the migration preserved the answers:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_evals.py ${ARGUMENTS:+--filter "$ARGUMENTS"} \
  --gold-cmd 'sqlite3 analytics/fixtures/warehouse.db'   # or your real warehouse CLI
```

Run from the repo root. Then:

1. Report the pass rate and every failing case with its missing/forbidden assertions.
   A case that fails on `numbers_ok` alone — right tables, right tier, wrong number — is
   the most serious result the suite produces. Lead with it.
2. For each failure, say which failure mode it is — **ambiguity** (agent picked a
   plausible wrong entity), **staleness** (doc no longer matches the model), or
   **retrieval** (the answer was documented and not found). The fix differs per mode.
3. Propose the doc edit for each. One line each, in the owning reference doc.
4. If this run is comparing against a previous one, print the before/after delta on the
   same slice and say plainly whether the change helped, hurt, or did nothing. Null
   results get recorded in `analytics/evals/NEGATIVE-RESULTS.md`, not buried.

Do not edit evals to make them pass. An eval that fails because it is wrong gets fixed
as a *separate* change with that reason stated.
