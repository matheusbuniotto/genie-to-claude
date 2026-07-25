# Metrics Catalog (tier 1 — try before any raw SQL)

<!-- not-a-domain-doc -->

Compiled metric definitions. A question that maps to a row here is answered by
aggregating the governed view, **not** by writing SQL against `fact_orders`. Humans own
these definitions; Claude may draft the *documentation* but never the definition.

## The governed view: `sem_orders`

One row per order, with the hygiene filter, the de-duplicated customer join, and the
named segments already applied. Aggregating it is the tier-1 path.

```sql
SELECT SUM(net_revenue) FROM sem_orders
WHERE order_date >= '2026-05-01' AND order_date < '2026-06-01'
```

Using it makes three wrong answers structurally impossible: you cannot omit the fraud
filter, cannot fan out on the per-user `dim_customer`, and cannot hand-roll a segment.
It returns exactly the same number as the correct hand-written query — verified on every
build by `fixtures/seed.py`.

## Measures

Additive measures compose over any window and dimension. Ratios are computed **from the
sums** — never averaged across days.

| Metric | Owner | Definition over `sem_orders` | Notes |
|---|---|---|---|
| `net_revenue` | finance-data | `SUM(net_revenue)` | refund-adjusted; provisional for 14d |
| `gmv` | finance-data | `SUM(gmv)` | pre-refund, pre-discount |
| `orders` | growth-data | `COUNT(DISTINCT order_id)` | |
| `aov` | growth-data | `SUM(net_revenue) / COUNT(DISTINCT order_id)` | denominator is orders |
| `refund_rate` | finance-data | `SUM(is_refunded) * 1.0 / COUNT(*)` | trailing metric, lags 14d |
| `active_customers` | growth-data | `COUNT(DISTINCT customer_id)` | non-additive: recompute per window, never sum daily counts |

## Dimensions

`order_date` (day/week/month, Sao_Paulo) · `channel_code` · `country_iso2` ·
`customer_segment` · `category` (items grain only — not on `sem_orders`)

## Segments (named canonical populations — use these, do not hand-roll)

Each is a flag on `sem_orders`; filter with `WHERE seg_x = 1`.

| Segment | Column | Means |
|---|---|---|
| `paying_b2b` | `seg_paying_b2b` | business accounts, free-email domains excluded |
| `new_customers` | `seg_new_customer` | first order falls on the order date |
| `excl_internal` | `seg_excl_internal` | employee and test accounts removed |

Hand-rolling a `WHERE` clause that reproduces one of these is the dominant wrong-answer
mode in this warehouse.

## When `sem_orders` doesn't cover it

Item/category questions (it has no item grain), attribution, and marketing spend fall
through to tier 2 — see [`orders.md`](orders.md) and [`marketing.md`](marketing.md).
Report `governed table` in the footer when you drop to tier 2.
