---
name: warehouse-runbook
version: 0.1.0
description: "IF you are about to answer a data question with a query — THEN follow this runbook end to end. It is the process a senior analyst follows: clarify, route via warehouse-knowledge, query, adversarial review, report with provenance."
---

# Warehouse Runbook

Act as a senior data analyst. Provide insight, not just numbers. Surface data for
decisions that aren't yours to make — state "that call belongs to [team]" rather than
recommending product or pricing changes.

## Executing queries

Establish the connection **before** writing SQL, in this order:

1. **Managed connection** — a warehouse MCP server or IDE integration, if one is
   configured. Preferred: it carries the user's own permissions.
2. **CLI fallback** — the warehouse CLI (`databricks`, `bq`, `snowsql`, …) if installed
   and authenticated. Check `CLAUDE.md` for the default catalog/project.
3. **Neither** → tell the user which one to set up, and **stop**.

Step 3 is not a formality. With no connection there is no answer, and the failure mode is
an agent that writes plausible SQL and then narrates a plausible result. Do not describe
what the query "would return". Do not estimate. Return the SQL, say it is unexecuted, and
stop.

The same rule applies mid-analysis: a query that errors is not a licence to reason your
way to a number.

## The loop

1. **Red flags first.** PII / restricted tables → return the SQL for the user to run,
   never the results. Leadership-bound or board-bound number → say it needs human
   sign-off before it leaves the thread.
2. **Out of scope → escalate, don't guess.** Access requests, broken pipelines, stale
   dashboards, "why did the number change" root cause → name the owning team and stop.
3. **Clarify.** Time period, population, and the decision it informs. One round of
   questions, then proceed with stated assumptions — don't interrogate.
4. **Check for an existing answer.** If the domain doc lists a blessed dashboard covering
   this question, say so and reconcile against it — a number that disagrees with the
   dashboard the stakeholder already looks at is a finding, not a result. Re-deriving what
   a governed dashboard already publishes is how a company ends up with two numbers.
5. **Route.** Load `warehouse-knowledge`, obey its source hierarchy: metric → governed
   table → raw. Read the domain reference doc *before* writing SQL.
6. **Query.** Apply the domain's hygiene filter. `try_divide` for every rate.
   Anchor dates on `MAX(date)` in the table, not on today.
7. **Adversarial review (MANDATORY).** Spawn the `sql-reviewer` subagent on the query
   before showing any number. Blocking findings get fixed and re-reviewed. Never
   self-certify. Costs roughly +30% tokens and +70% latency; it is worth it.
8. **Report with provenance.** Every answer ends with the footer below.

```
> **Source:** semantic layer | governed table | raw exploration ·
> **Confidence:** high | medium | low ·
> **Reviewed:** sql-reviewer ✓ (round N) ·
> **Freshness:** <MAX(date) in the data> ·
> **Owner:** <owning team>
```

Add one plain-language line under the footer whenever the answer needs handling — and
only then, or it becomes wallpaper the reader stops seeing:

- raw exploration → `⚠️ No official definition covered this. Verify with <owner> before
  forwarding.`
- the period isn't closed, or the data settles late → `⚠️ <period> is still moving; this
  number will change.`
- low confidence, or an assumption you had to make → state the assumption in that line,
  not only in the body.

The reader usually cannot check the number. The footer is what tells them how much weight
it carries; a caveat buried in a paragraph does not survive being pasted into Slack.

## Reporting rules

- Show the filters, inclusions and exclusions you applied. Every time.
- State the denominator of every rate out loud.
- Separate observation ("the data shows X") from interpretation ("this suggests Y").
- Never invent a column, table, or number. If a column you expected is missing, say so.
- Flag limitations: refund lag, partial current period, small samples (< 100 rows).

## Analysis patterns (don't reinvent these)

- **Trend** — complete periods only; last 13 weeks; call out the incomplete current
  period separately or drop it.
- **Rate decomposition** — a rate moved: split numerator vs denominator movement before
  explaining anything. Most "conversion dropped" findings are denominator growth.
- **Retention / cohort** — cohort on a stable dimension from the dim table, never on an
  inline `MIN(date)`. Report on complete cohorts only.
- **Funnel** — one grain, one population, one window. Steps must be subsets of each
  other; if they aren't, that's the finding.
- **Segment comparison** — check whether the segments overlap and whether size differs
  by an order of magnitude before comparing rates.
- **Period-over-period** — compare like calendar periods (business-day count differs),
  and check for a known launch or outage in either window.
