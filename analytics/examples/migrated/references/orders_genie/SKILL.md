---
name: Orders & Revenue
description: Marketplace order and revenue questions for the growth and finance teams.
---

# Orders & Revenue Tables

<!-- migrated from a Genie space by migrate_genie.py.
     TODO markers are what Genie has no field for — a human fills them in. -->

## Quick Reference

### Use For / Do NOT Use For
TODO: state the routing trigger explicitly — 'IF the question is about X → use this. DO NOT use for Y (→ other-domain/SKILL.md).' Without it the router can't tell this domain apart from its neighbours.

### Business Context
Marketplace order and revenue questions for the growth and finance teams.

### Entity Grain
TODO: what one row of the primary table represents.

### Standard Hygiene Filter
```sql
WHERE is_test = false AND order_status NOT IN ('cancelled', 'fraud_blocked')
```

### Ownership & Freshness
- **Owner**: TODO (ask a human — no Genie field carries this)
- **Refresh cadence / lag**: TODO · **Settles late?**: TODO

<!-- the runbook's provenance footer prints Owner and Freshness verbatim; while
     these say TODO, every answer from this domain ships unattributed. -->

## Metrics (tier 1 — required first resort)

### `analytics.core.revenue_metrics`
- **Measures**: net_revenue, gmv, orders, aov, refund_rate
- **Dimensions**: order_date, channel_code, country_iso2, customer_segment
- **Named segments**: TODO (hand-rolling a WHERE clause that reproduces one
  is the dominant wrong-answer mode)
- **Owner**: TODO

## Full Detail

Dimensions, key tables, blessed dashboards, gotchas and query patterns: [`reference.md`](reference.md).
