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

**No metric view covers this domain.** `sem_orders` ([`metrics.md`](metrics.md)) is
orders-only and carries no spend or attribution. Tier 2 — the governed tables below — is
the top of the ladder here, so say `governed table` in the provenance footer and name the
attribution model in the answer.

## Dimensions

- **Channel** is `channel_name` here (`'Web'`, `'iOS'`, `'Android'`) but `channel_code`
  (`'web'`, `'ios'`, `'and'`) in `fact_orders`. Join on the code, display the name.
- **Attribution model** — `attribution_model` ∈ `'last_touch'` (default, matches the
  blessed dashboard), `'first_touch'`, `'linear'`. Never sum across models; each row
  exists once per model and totals will triple.
- **Currency** — spend is `_usd` at platform FX; orders are `_brl` at order-date FX.
  Converting between them for ROAS requires `dim_fx_daily`. State the conversion used.
- **Date** — `spend_date` is the platform's local date, not Sao_Paulo. Off-by-one against
  `order_date` is expected at the day grain; roll up to weeks for comparisons.

## Key Tables

### `analytics.marketing.fact_marketing_spend`
- **Grain**: campaign × day × platform · **Scope**: paid channels only, 2022-03 onward
- **Exclusions**: organic and direct traffic have no rows here — a channel-share
  denominator built from this table silently excludes all organic.
- **Usage**: spend, CPC, CPM, campaign budgets. Join to `dim_campaign` on `campaign_id`.

### `analytics.marketing.fact_attributed_revenue`
- **Grain**: order × attribution model · **Scope**: attributed orders only
- **Usage**: ROAS, CAC, channel revenue contribution.
  **IF the question is about attributed or channel-credited revenue → use this.
  DO NOT use it for total company revenue** — unattributed orders (~20%) have no row
  here, so it under-reports `fact_orders` and always will. Total revenue is
  [`orders.md`](orders.md).
- Always filter `attribution_model = 'last_touch'` unless the asker named another.

### `analytics.marketing.dim_marketing_touch`
- **Grain**: one touchpoint · **Usage**: path analysis, touch counts, time-to-convert.
- **Do NOT use for**: revenue. Touches have no monetary value attached; joining them to
  orders fans out revenue by the number of touches.

## Gotchas

- **Attributed ≠ total.** The single most common wrong answer in this domain is answering
  "how much revenue did we make" from `fact_attributed_revenue`. It is ~20% low, and the
  gap grows with organic traffic.
- **Model triple-counting.** Forgetting `attribution_model` in a `WHERE` clause returns
  3x every number, and the result looks like a great quarter.
- **Touch fan-out.** Joining `dim_marketing_touch` to orders multiplies revenue by the
  touch count. If ROAS looks 4x better than usual, check this first.
- **Organic has no spend row.** Channel-share and blended-CAC denominators must come from
  [`orders.md`](orders.md), not from this domain's tables.
- **CAC denominator.** New customers, not orders, not attributed orders. The
  `new_customers` segment in [`metrics.md`](metrics.md) is the governed population.
- **Platform lag.** Spend restates for ~72h after the fact. Anchor on `MAX(spend_date)`
  and caveat anything inside that window.

## Best Practices / Common Query Patterns

- Default cut for channel performance: last 13 complete weeks, `last_touch`, spend and
  attributed revenue side by side, with the unattributed share stated.
- ROAS = attributed revenue ÷ spend, same window, same currency, `try_divide`. Say which
  attribution model produced it — a ROAS without a named model is not a number.
- Comparing channels: check spend magnitude first. A channel with 2% of budget will have
  noisy ROAS, and ranking it first is an artefact.

## Cross-References

- Total revenue, GMV, AOV, refunds → [`orders.md`](orders.md)
- Metric and segment definitions → [`metrics.md`](metrics.md)
