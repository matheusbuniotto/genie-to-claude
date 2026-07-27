---
name: Orders & Revenue
description: "IF the question is about GMV, net revenue, AOV, refunds, or order/item counts -> use this. DO NOT use for attributed or channel-credited revenue (-> marketing/SKILL.md)."
---

# Orders & Revenue Tables

## Quick Reference

### Business Context
Every completed purchase on the marketplace. One order can contain many items and is
paid in one transaction. Refunds are *not* deletions — they arrive as separate rows
later, so any revenue number is provisional for ~14 days.

### Entity Grain
`fact_orders` = one row per order. `fact_order_items` = one row per SKU per order.
Summing item revenue and order revenue gives different totals (shipping is
order-level); pick the grain that matches the question and say which you used.

### Standard Hygiene Filter
Every query in this domain applies:
```sql
WHERE is_test = false
  AND order_status NOT IN ('cancelled', 'fraud_blocked')
```
Omitting it inflates GMV by ~5% and is the most common review finding.

### Ownership & Freshness
- **Owner**: finance-data (same team owns the blessed dashboards below)
- **Refresh**: daily · **Settles late**: yes — refunds land for ~14 days, so the trailing
  two weeks are provisional. Anchor windows on `MAX(order_date)`, not `CURRENT_DATE`.

## Metrics (tier 1 — required first resort)

`sem_orders` covers this domain: net revenue, GMV, AOV, order and customer counts, by
date, channel, country and segment. It bakes in the hygiene filter, the de-duplicated
customer join and the named segments — aggregate it before reaching for any table below.
Measures, segments and their owners are in [`../metrics.md`](../metrics.md); the cases it
does *not* cover (item/category grain, attribution, marketing spend) are listed there too.

## Full Detail
See [`references/orders.md`](references/orders.md) for dimensions, key tables, blessed
dashboards, gotchas and query patterns.
