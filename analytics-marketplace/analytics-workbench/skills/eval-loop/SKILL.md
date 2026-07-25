---
name: eval-loop
version: 0.1.0
description: "IF you are writing offline evals for an analytics agent, running the eval suite, measuring whether a doc or skill change helped (ablation), gating a domain launch, or harvesting a stakeholder correction into a test — THEN invoke this skill. DO NOT invoke for answering data questions."
---

# The eval loop

An analytics agent with no eval suite has unknown accuracy, and unknown accuracy in a
system whose users can't check the answer is the actual risk. Evals are how you find out
which failure mode — ambiguity, staleness, retrieval — is still leaking.

Eval sets live in `analytics/evals/<domain>.jsonl`. The runner is
`${CLAUDE_PLUGIN_ROOT}/scripts/run_evals.py`.

## Case format

```json
{"id": "orders-003", "domain": "orders",
 "question": "Total GMV for Brazil in Q1 2026",
 "expect_tier": "governed_table",
 "must_include": ["fact_orders", "is_test", "fraud_blocked"],
 "must_not_include": ["orders_v1"],
 "note": "hygiene filter mandatory; orders_v1 is deprecated"}
```

`expect_tier` is one of `semantic_layer`, `governed_table`, `raw`, `escalate` — it grades
the provenance footer, which is how you keep the agent honest about *how* it answered.
`gold_sql` is optional reference SQL: by default it is documentation for humans, and
grading never diffs numbers. `--gold-cmd` promotes it to an assertion — see below.

## Number parity (migrations)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_evals.py --filter '^orders_genie-' \
  --gold-cmd 'sqlite3 analytics/fixtures/warehouse.db'
```

Every case carrying `gold_sql` has that SQL executed, and the agent's answer must state
the numbers it returned (0.5% tolerance, rates matched at either scale). Failures print
`numbers_ok=False`.

Use it where a gold number is genuinely authoritative — **a migration is the case that
matters**: the gold SQL came out of the tool you are replacing, so parity is the whole
question. "Claude cited the right table" is not the promise anyone is making to a
stakeholder; "Claude returns what Genie returned" is. A case that passes every assertion
except `numbers_ok` is the silent failure this suite otherwise cannot see.

Two standing rules still apply. Parity is only meaningful against an **anchored** gold
query — a snapshot date or a fixed window, never "last month", or the assertion rots by
tomorrow. And parity is an *addition* to the assertions, not a replacement: an agent that
prints the right number off the wrong table got lucky, and `must_include` is what catches
it. Leave parity off for the ordinary suite, where a number-free grade is what keeps the
set alive as data moves.

`--gold-cmd` takes any shell command reading SQL on stdin. Three-part names are stripped
to bare tables so gold SQL runs against an offline fixture; pass `--keep-qualified` when
pointing at the real warehouse. It is not a dialect translator — gold SQL that leans on
the source warehouse's dialect should run against that warehouse.

## Rules that keep the suite useful

- **Grade the query and the reasoning, not the number** — by default. A number-based
  assertion is wrong the next time the data lands. Assert on the table, the filter, the
  metric name, the tier. The exception is a migration, where the old system's number is
  the point: pin the question to a snapshot date and turn on number parity (below).
- **Anchor to stable objects** — a fact table and a fixed date range, never "last month".
- **Two sources of cases.** *Dashboard-based*: the questions stakeholders actually ask,
  generated from the dashboard catalogue and human-validated. *Long tail*: generated from
  business context (roadmaps, table docs) to cover the rest of the domain.
- **Every correction is a case.** Any time a stakeholder says "wrong table" or "you
  missed the fraud filter", that thread becomes an eval before the fix ships.
- **A few dozen per topic.** Past that, returns diminish, and the ceiling drops with each
  model generation. Calibrate by checking how well offline accuracy predicts online.
- **Target ~100%, and expect the target to lie.** Full marks means no obvious gaps, not
  no wrong answers. Coverage is the assumption doing all the work.
- **Gate per domain.** A domain isn't announced to its stakeholders until its slice
  passes (~90% to start). This forces doc fixes before users meet the failures.

## Running

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_evals.py                     # everything
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_evals.py --filter '^orders-' # one slice
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_evals.py --selftest          # grader only
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_evals.py --agent-cmd ./bot   # a different agent
```

Run from the repo root. Exits non-zero under 90%. Each case appends a row to
`analytics/evals/results.jsonl` with the docs SHA, model, tokens, duration and
per-assertion outcome.

`--agent-cmd` takes any shell command that reads the question on stdin and prints the
answer on stdout. Two uses: exercising the harness against a scripted stub without
burning tokens, and running the *same* eval set against another surface — the Slack bot,
a hosted app, an MCP client. If one surface scores differently from another on the same
questions, they aren't reading the same canonical skill, which is the whole problem that
one-canonical-repo-synced-everywhere exists to prevent.

**Two CI tiers, not one.** The structural gate (`scripts/check.py` — evals well-formed,
docs registered in the router, links resolve, doc claims still true against the fixture)
costs nothing and runs on every PR. The eval suite costs tokens, so it runs on demand or
on eval-affecting PRs. Collapsing them into one job means either the cheap checks don't
run often enough or the expensive ones bankrupt you. See `.github/workflows/analytics.yml`.

**Give the suite a warehouse it can reach.** Evals that need production credentials only
run where those credentials exist, which in practice means they stop running. A seeded
fixture warehouse — small, deterministic, containing every gotcha the docs describe — lets
the suite run offline and in CI. Assert the docs' numeric claims against that fixture too:
a doc that says "the fraud filter is worth ~5% of GMV" should fail a build when it stops
being true. See `analytics/fixtures/seed.py` for the pattern.

**Write assertions that fail for the right reason.** Assert on behaviour, not phrasing.
For a PII refusal, `must_not_include: ["@"]` catches a leaked address no matter how the
refusal is worded; `must_include: ["run"]` just tests whether the model happened to use
that word. When an eval and a reference doc disagree on wording, fix the doc to be
canonical — don't loosen the assertion.

**Store results as telemetry, not test logs.** Load that file into a warehouse table.
"Did that change help?" should be a query with history behind it, not a memory of
yesterday's CI run — slow regressions are invisible in a single run.

## Ablation

Every structural decision — expose this source or not, is the reviewer sub-agent worth
its latency, merge these two skills — is settled by holding the eval set fixed, changing
exactly one thing, and comparing pass rates. Each run costs about an hour and replaces a
long argument.

1. Baseline run on the affected slice.
2. Change one component. One.
3. Re-run the same slice, same model, same cases.
4. Put the delta in the PR description. Every meaningful doc or skill edit gets this.

**Design for null results.** The most valuable known ablation was negative: giving the
agent grep access to thousands of prior dashboard and notebook SQL files moved accuracy
less than a point, even though it demonstrably read them and the answer was present ~80%
of the time it got a question wrong. Access was never the bottleneck; structure was. A
null result that redirects a roadmap is worth more than a win.

**Keep a list of what didn't work** in `analytics/evals/NEGATIVE-RESULTS.md`, one line
each. Known entries: stacking more rounds of doc refinement past ~3 iterations (docs got
longer, not better); downgrading the adversarial reviewer to a cheaper model (lost most
of the accuracy gain for no real speedup).

## Harvesting corrections

The loop only closes if corrections come back in. Periodically, or when asked:

1. Scan stakeholder threads for correction language — "wrong table", "that's not how we
   define", "you forgot", "should be net".
2. For each: draft **one line** for the owning reference doc, and one eval case.
3. Open a PR tagged to the domain owner. Keep it a markdown edit and nothing else — the
   fix path has to stay cheap or owners disengage.

## What evals still won't catch

The silent failure: wrong, plausible, forwarded without objection. Partial mitigations —
the provenance footer, human sign-off on anything leadership-bound, and a standing
per-domain KPI eval that checks the blessed dashboard daily. None of them solve it.
