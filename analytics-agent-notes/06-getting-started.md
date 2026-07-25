# Getting started

Source: [How Anthropic enables self-service data analytics with Claude](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude)

Minimum viable version: **a handful of canonical datasets + a few dozen offline evals + one thin knowledge skill.** Everything else in the source article is what got added once that was solid.

Not all practices fit every team — align on these before over-building:

- **How important is a correct answer today vs. later?** Building infra to cover current model shortfalls can become moot once models improve; waiting has less overhead but may not match your risk tolerance.
- **How will business complexity change over time?** Overkill if you don't produce much data, have few consumers, or the data model will stay simple.
- **How technical is the audience?** Data scientists who can spot a wrong answer tolerate more error than an audience with no data-model familiarity.
- **How much are you willing to spend for accuracy?** Things like adversarial validation raise accuracy but cost more tokens/latency.
- **What's your access-control / privacy posture?** More context = better agent performance, but broad data access cuts against governance. Determines one broad agent vs. many scoped agents.

Bottom line: gains come from addressing the three failure modes — collapse ambiguity into one governed answer, make it discoverable, flag staleness.

## Skill file skeleton (top-level warehouse skill)

```
---
name: [warehouse-skill]
version: [x.y.z]
description: "IF the user asks to query [the company]'s data warehouse for any
  [list of business domains] question — THEN invoke this skill. DO NOT invoke
  for [adjacent engineering tasks] or questions with no data-warehouse component."
---

# [Warehouse] Skill Instructions
## Description
Single source of truth for safe/effective [warehouse] querying.
Act as a Data Analyst: strategic insights, data-driven recommendations,
but defer out-of-scope decisions to the owning team — don't take a position.

## Executing queries (priority order)
1. Managed connection (if available)
2. CLI fallback (if installed)
3. Neither → ask user to authenticate, then stop

---
# Semantic Layer (REQUIRED first step)
Mandatory default path for every data question. Raw SQL is fallback only,
used after the semantic layer is shown not to cover the ask.

## Required workflow
1. Load the semantic layer
2. Discover measures/dimensions by keyword; always check named segments
   (hand-rolled WHERE clauses recreating them = dominant wrong-answer mode)
3. Compile spec → SQL → execute
4. Fallback to raw SQL via reference docs only if discovery/compile fails

Don't bail early on excuses like "needs custom date filtering" or "needs a
join" — the semantic layer usually already covers these.

---
# PART 1: MUST KNOW
- Check for red flags (PII, gated domains, high-stakes asks) first
- Escalate out-of-scope requests (access, pipeline troubleshooting, root-cause
  claims) rather than guessing
- Clarify time period, segment, and the business decision behind the ask
- Entity disambiguation: flag ambiguous terms and clarify before answering
- Never fabricate data/columns; always separate observation from interpretation

# PART 2: HOW TO DO
- Adversarial SQL review is MANDATORY before any final answer — no self-certifying
- Every answer ends with a provenance footer: source tier, confidence,
  reviewer sign-off, freshness, owning team

# PART 3: DATA REFERENCES
- One entry per business domain pointing to references/[domain].md
- Troubleshooting guide for missing info and field-naming gotchas
  (e.g. "use field_x_v2, NOT field_x")
```
