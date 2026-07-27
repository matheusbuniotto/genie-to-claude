---
name: Marketing & Attribution
description: "IF the question is about spend, CPC, ROAS, CAC, channel/campaign performance, or touch paths -> use this. DO NOT use for total company revenue (-> orders/SKILL.md) -- attributed revenue is ~20% low by construction."
---

# Marketing & Attribution Tables

## Quick Reference

### Business Context
Paid and organic acquisition: spend, campaigns, touchpoints, and the revenue credited to
them. Attribution is a *model*, not a fact — every number in this domain is "revenue
under model X", and the model must be named in the answer.

### Entity Grain
`fact_marketing_spend` = one row per campaign per day per platform.
`dim_marketing_touch` = one row per touchpoint per customer. A conversion has many
touches; the attribution model decides how credit is split across them.

### Standard Hygiene Filter
```sql
WHERE is_test_campaign = false
  AND spend_usd >= 0          -- platform refunds arrive as negative rows
```
Negative spend rows are real credits from ad platforms. Keep them in *spend totals*, drop
them from CPC/CPM ratios — they make the denominator meaningless.

### Ownership & Freshness
- **Owner**: growth-analytics (attribution model changes are theirs to approve)
- **Refresh**: daily, but platform spend backfills for ~3 days and attribution re-runs
  nightly — a number pulled today can move tomorrow. Anchor on `MAX(spend_date)`.

## Metrics (tier 1 — required first resort)

**No metric view covers this domain.** `sem_orders` ([`../metrics.md`](../metrics.md))
is orders-only and carries no spend or attribution. Tier 2 — the governed tables below —
is the top of the ladder here, so say `governed table` in the provenance footer and name
the attribution model in the answer.

## Full Detail
See [`reference.md`](reference.md) for dimensions, key tables, gotchas and query
patterns.
