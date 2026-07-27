---
name: reference-doc
version: 0.1.0
description: "IF you are writing, reviewing, or fixing a domain reference doc — or a data-model change needs its doc updated, or an eval failure traces back to a missing gotcha — THEN invoke this skill. DO NOT invoke for writing SQL or answering data questions."
---

# Authoring reference docs

These docs are the agent's map of the warehouse. They exist to collapse a concept
("revenue for product X") onto exactly one governed table, column and definition. They
are written **for retrieval by an LLM**, not for onboarding a human.

Without docs like these, measured accuracy on analytics questions sits around 21%. With
them, above 95%. This is the highest-leverage file type in the repo — and the fastest to
rot: unmaintained, accuracy drifts from ~95% to ~65% in about a month.

## Rules

- **One skill-folder per business domain**, named for the domain:
  `analytics/references/orders/SKILL.md` + `analytics/references/orders/reference.md`
  — or wherever `CLAUDE.md` says the project keeps them. A few dozen domains is the
  expected steady state. This is a real Claude Skill shape (YAML frontmatter,
  progressive disclosure) — `SKILL.md` is what the router scans across every candidate
  domain, so it stays short; `reference.md` holds the deep mechanics (dimensions, key
  tables, gotchas, query patterns) and is opened only for the one domain that wins the
  routing decision. `reference.md` sits flat next to `SKILL.md`, not nested in its own
  subfolder — per Anthropic's skill-authoring guidance, a nested `references/`
  subfolder is for a skill with *multiple* distinct reference files; one domain here
  has exactly one.
- **Every doc is registered** in `analytics/references/INDEX.md` as a row linking
  `<domain>/SKILL.md`, with a "use for" and a "do NOT use for". The INDEX is the router;
  an unregistered doc is invisible.
- **Describe, don't prescribe.** Grain, scope, exclusions, join keys, required filters,
  and the mechanics of each gotcha. Step-by-step query recipes go stale and get copied
  wrong; a stated grain does not.
- **Routing triggers are explicit**: "IF the question is about experiment lift → use
  this. DO NOT use for raw event counts." Ambiguity here is the retrieval failure.
- **Humans own definitions, Claude owns prose.** Draft column descriptions, grain notes
  and gotcha wording with Claude; a metric definition is never LLM-generated.
  Auto-generating metric definitions from raw tables and query logs tested net-negative:
  it produces plausible definitions that encode the exact ambiguity you are removing.
- **Same PR.** A change to a reporting model and the change to its doc ship together, or
  the doc is already wrong. Aim for ~90% of data-model PRs touching a doc.
- **Prune.** Scaffolding written for a model generation that no longer needs it is now
  just tokens between the agent and the answer. Delete it.

## Skeleton

`SKILL.md` — short, frontmatter-led, scanned across every candidate domain before one
is picked:

```markdown
---
name: [Domain]
description: "IF the question is about [X] -> use this. DO NOT use for [Y] (-> other-domain/SKILL.md)."
---

# [Domain] Tables

## Quick Reference
### Use For / Do NOT Use For — [the routing trigger, same substance as the description above]
### Business Context — [what this domain means in plain words]
### Entity Grain — [what one row represents]
### Standard Hygiene Filter — [the filter every query in this domain applies]
### Ownership & Freshness — [owning team, refresh cadence, whether it settles late]

## Metrics (tier 1 — required first resort)
- [The metric view / semantic-layer entry that covers this domain, its named segments,
  and the questions it answers without raw SQL. If none exists, say so explicitly.]

## Full Detail
See reference.md for dimensions, key tables, blessed dashboards, gotchas and query
patterns.
```

`reference.md` (flat, next to `SKILL.md`) — opened only once `SKILL.md` has won the
routing decision; everything here assumes the reader already has the Quick Reference:

```markdown
## Dimensions
- [How key dimensions are encoded, and where the same concept is named
  differently across tables]

## Key Tables
### [table_name]
- **Grain**: [...] · **Scope/exclusions**: [...]
- **Usage**: [when to use it, when NOT to, join keys, required filters]
[... one short section per governed table; mark deprecated ones as deprecated ...]

## Blessed Dashboards
- [The governed dashboard that already answers each common question, and the number
  it publishes — so the agent reconciles against it instead of re-deriving it]

## Gotchas
- [The wrong-answer modes a senior analyst would warn you about, with the mechanism]

## Best Practices / Common Query Patterns
- [Default cuts, and the patterns where the exact query form is the hard part]

## Cross-References
- [Neighbouring domain docs that own adjacent questions]
```

A domain small enough that this split feels like busywork can keep everything in
`SKILL.md` and skip `reference.md` — the split exists for when Key Tables + Gotchas
would otherwise bloat the file the router scans for every unrelated question too.

## Writing each section well

**Business Context** — plain words, including what is *not* in scope. Two sentences.

**Entity Grain** — say what one row is, and name the trap: "summing item revenue and
order revenue gives different totals; shipping is order-level."

**Hygiene Filter** — the literal SQL, in a code block, with what breaks without it
("omitting the fraud filter inflates GMV by ~3%"). Quantify when you can; a number makes
the agent take it seriously.

**Ownership & Freshness** — the runbook's provenance footer prints an owner and a
freshness on every answer; this is where it reads them from. Name the team, not a person.
An empty owner means every answer from this domain ships unattributed.

**Metrics** — always present, even when the answer is "no metric view covers this domain".
Omitting the section reads as "tier 1 was forgotten" and starts the agent at tier 2.

**Dimensions** — encodings and cross-table naming drift: `channel_code` here,
`channel_name` there; ISO-2 in one table, ISO-3 in the legacy one.

**Gotchas** — each entry names the mechanism, not just the rule. "`net_revenue_brl` is
already refund-adjusted; subtracting `fact_refunds` double-counts" beats "don't subtract
refunds". Prime sources: every stakeholder correction, every eval failure, every
`DOC GAP` line from `analysis-reviewer`.

**Cross-References** — where the neighbouring question goes. Cheap to write, and it stops
the agent from answering a question the doc doesn't own.

## Maintenance loop

1. An eval fails, a stakeholder corrects an answer, or QA reports a `DOC GAP`.
2. Write the fix as **one line** in the right doc. Boring on purpose — if fixing costs
   more than a line, domain owners stop doing it.
3. Add the case to `analytics/evals/<domain>.jsonl` so it can't regress.
4. Re-run that eval slice (`eval-loop` skill) and put the before/after delta in the PR.
