<!-- reference detail for orders_genie/SKILL.md -->

## Dimensions

- `channel_code` — also called: channel, platform, surface
- `net_revenue_brl` — also called: revenue, net revenue

## Key Tables

### `analytics.core.fact_orders`
- **Grain**: TODO · **Scope/exclusions**: TODO
- **Usage**: One row per order. All marketplaces, 2021-01-01 onward. Includes test and cancelled orders — filter them out.

### `analytics.core.fact_order_items`
- **Grain**: TODO · **Scope/exclusions**: TODO
- **Usage**: One row per SKU per order. Use for product and category cuts only — item revenue excludes shipping.

### Deprecated / near-duplicate tables
TODO: the tables that look like they answer this domain and must not be used,
and why. A Genie space lists what to query, never what to avoid — so this is the
list the evals' `must_not_include` is built from.

## Blessed Dashboards

TODO: the governed dashboard that already publishes each common number here, so
the agent reconciles against it instead of re-deriving it. A query that disagrees
with the dashboard the stakeholder already reads is a finding, not a result.

## Gotchas

- Always exclude test and fraud-blocked orders: is_test = false AND order_status NOT IN ('cancelled', 'fraud_blocked').
- "Last month" means the last complete calendar month, never trailing 30 days.
- net_revenue_brl is already refund-adjusted — never subtract refunds again.
- Revenue for the trailing 14 days is provisional because refunds arrive late.
- Never mix _brl and _usd columns in one series; they use different FX conventions.
- SQL function available: analytics.core.f_orders_in_window(start_date DATE, end_date DATE)

<!-- TODO: these are Genie's free-text rules verbatim. A good gotcha names the
     mechanism, not just the rule: 'net_revenue is already refund-adjusted;
     subtracting fact_refunds double-counts' beats 'do not subtract refunds'. -->

## Best Practices / Common Query Patterns

- **Active customers** — `COUNT(DISTINCT customer_id)`
  - Count accounts, not users. COUNT(DISTINCT user_id) inflates B2B by ~1.7x.
  - asked as: active customers, actives

<!-- TODO: a human owns every metric definition. Genie snippets are candidates,
     not definitions — promote each into the semantic layer or delete it. -->

## Cross-References

- TODO: neighbouring domain docs that own adjacent questions, and the questions
  this doc must hand off to them.
