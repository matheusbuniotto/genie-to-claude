---
name: warehouse-knowledge
version: 0.1.0
description: "IF the user asks anything that needs numbers out of the data warehouse — revenue, orders, customers, usage, marketing — THEN invoke this skill to find the right source before writing any SQL. DO NOT invoke for pipeline debugging, access requests, or questions with no data component."
---

# Warehouse Knowledge (router)

Declarative knowledge: *where the answer lives*. The process for producing an answer is
`warehouse-runbook`. Never write SQL before this skill has resolved the question to a
source.

## Where the project's knowledge lives

Reference docs are **project-owned**, not shipped with this plugin — they change daily
and live in the repo next to the models they describe.

1. Read `analytics/references/INDEX.md` — the domain map, plus the terms that must be
   disambiguated before querying. If `CLAUDE.md` names a different path, use that.
2. From the map, open the **one** domain's `SKILL.md` that owns the question (frontmatter
   + Quick Reference + tier-1 metrics — enough to route and apply the hygiene filter).
   Only pull in that domain's sibling `reference.md` (key tables, gotchas, query
   patterns) once it's the winner — reading it for every candidate domain defeats the
   point of a short, scannable `SKILL.md`. Open a second domain only if the question
   genuinely spans domains.
3. No `INDEX.md` → list `analytics/references/*/SKILL.md` (and any legacy flat `*.md`),
   say the project isn't set up yet, and point at `/analytics-workbench:new-domain`.

Reading the whole reference directory is a failure, not thoroughness. The point of the
map is to narrow a million-field warehouse to one file before the first query.

## Source hierarchy — go down, never skip up

| Tier | Source | Use when |
|---|---|---|
| 1 | **Semantic layer / metric views** | Always try first. A defined metric returns the same number as the BI tool, with joins, grain and filters already baked in. |
| 2 | **Governed tables** named in the domain doc | No metric covers the ask. Read the doc's grain, hygiene filter and gotchas *before* writing SQL. |
| 3 | **Raw exploration** | Nothing above covers it. Say so in the footer — tier 3 means the consumer should verify before forwarding. |

**Don't bail early.** None of these justify dropping a tier:
- "needs a custom date window" → time dimensions handle it
- "needs a join" → the metric already encapsulates its joins
- "needs a segment or cohort filter" → check the doc's **named segments** first;
  hand-rolling a `WHERE` clause that reproduces a named segment is the single most
  common wrong-answer mode
- "the metric name doesn't match the user's wording" → search synonyms before giving up
- "it's just a quick count" → quick counts are what get forwarded to leadership

## Ambiguity is resolved, not guessed

Before querying, check the domain doc for the meaning of every load-bearing word in the
question. Usual culprits: *revenue* (gross / net / recognized), *customer* (account vs
person), *active*, *last month* (last complete calendar month, not trailing 30 days),
timezone, and which date column reporting uses. If the doc doesn't settle it, ask — one
round, then proceed with the assumption stated in the answer.

## When information is missing

Table in no doc → say so, don't guess a name. Doc contradicts the schema → trust the
schema, flag the drift, offer to fix the doc. Unknown enum value → `SELECT DISTINCT`
before filtering on it; a typo'd filter returns a clean, plausible, empty result and
nobody notices.
