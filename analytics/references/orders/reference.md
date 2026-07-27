<!-- reference detail for orders/SKILL.md -->

## Dimensions

- **Channel** is `channel_code` here (`'web'`, `'ios'`, `'and'`) but `channel_name`
  (`'Web'`, `'iOS'`, `'Android'`) in `dim_marketing_touch`. Join on the code, display
  the name.
- **Country** is ISO-2 in `fact_orders`, ISO-3 in the legacy `orders_v1`. Do not union.
- **Date**: `order_date` (Sao_Paulo, use for reporting) vs `created_at` (UTC, use for
  latency analysis). They disagree for ~4% of orders near midnight.

## Key Tables

### `analytics.core.fact_orders`
- **Grain**: one order · **Scope**: all marketplaces, 2021-01-01 onward
- **Exclusions**: test orders and cancelled orders are present, not removed — apply the
  hygiene filter yourself.
- **Usage**: default source for order counts, GMV, AOV, net revenue.
  `net_revenue_brl` is already refund-adjusted as of the last refresh; do **not** subtract
  `fact_refunds` again (double-counting).
- **Joining `dim_customer`**: that table is one row per *user*, not per account, so a
  naive join on `customer_id` multiplies every B2B order by its seat count (~3x). Join to
  a de-duplicated subquery, or aggregate orders first and join after.

### `analytics.core.fact_order_items`
- **Grain**: one item per order · **Scope**: mirrors `fact_orders`
- **Usage**: product/category questions only. Join to `fact_orders` on `order_id` and
  re-apply the hygiene filter — item rows survive an order cancellation.
- **Do NOT use for**: revenue totals. Item revenue excludes shipping and gift wrap.

### `analytics.core.orders_v1` — **DEPRECATED**
Frozen 2023-06. Present only for pre-2021 history. If a question needs it, say the data
is unmaintained in the answer.

## Blessed Dashboards

- **Revenue Weekly** (finance-data) — net revenue, GMV and AOV by complete week and
  channel. The company-canonical revenue number. If a query disagrees with it, reconcile
  before reporting; a mismatch is a finding, not a result.
- **Refund Monitor** (finance-data) — refund rate and refund lag by week.

## Gotchas

- **Refund lag**: revenue for the trailing 14 days is provisional. Always caveat it.
- **Double refund subtraction**: `net_revenue_brl` is already net. See above.
- **Currency**: `*_brl` columns are converted at order-date FX, `*_usd` at month-end FX.
  Mixing them across a month boundary produces numbers that reconcile with nothing.
- **AOV denominator**: orders, not customers, not items. State the denominator.
- **Free-email exclusion**: for B2B cuts, exclude known free-email domains
  (`dim_customer.is_free_email_domain`), but keep custom company domains.
- **Restricted column**: `dim_customer.customer_email` is PII. Return the SQL for the
  requester to run themselves; never put addresses in a response, a summary, or a file.
  Aggregates over it (counts, domain distributions) are fine.

## Best Practices / Common Query Patterns

- Default cut for "how is revenue doing": net revenue by complete week, last 13 weeks,
  split by `channel_code`.
- Rate metrics: always `SAFE_DIVIDE` / `try_divide` — refund rate on a zero-order day is
  a real occurrence.
- Cohorting: cohort on `first_order_date` from `dim_customer`, never on
  `MIN(order_date)` computed inline — it silently ignores the hygiene filter.

## Cross-References

- Attributed revenue, ROAS, CAC, campaign cuts → [`../marketing/SKILL.md`](../marketing/SKILL.md).
  Attributed revenue is ~20% below total revenue by construction; do not substitute one
  for the other.
- Metric and segment definitions → [`../metrics.md`](../metrics.md)
- Subscription/recurring revenue and customer lifecycle are **not documented yet**. Say so
  rather than answering from `fact_orders` — recurring revenue is not in this domain.
