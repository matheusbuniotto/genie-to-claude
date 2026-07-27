# Reference index — read this before any query

The router for `warehouse-knowledge`. One row per domain doc. An unregistered doc is
invisible to the agent, so register it here the moment you create it.

## Domain map

| Domain | Doc | Use for | Do NOT use for |
|---|---|---|---|
| Metrics catalog | [`metrics.md`](metrics.md) | any question naming a KPI; check here before opening a domain doc | table-level mechanics |
| Orders & revenue | [`orders/SKILL.md`](orders/SKILL.md) | GMV, net revenue, AOV, refunds, order and item counts | attributed or channel-credited revenue (→ `marketing/SKILL.md`) |
| Marketing & attribution | [`marketing/SKILL.md`](marketing/SKILL.md) | spend, CPC, ROAS, CAC, channel and campaign performance, touch paths | total company revenue (→ `orders/SKILL.md`) — attributed revenue is ~20% low by construction |

<!-- one row per domain; a few dozen rows is the expected steady state -->

**Not documented yet**: subscriptions/MRR, customer lifecycle, product usage. Say
plainly that the domain is **not documented** — never improvise an answer from a
neighbouring table.

## Disambiguate before querying

These words mean more than one thing in this business. Resolve them, or ask, before the
first query — never pick the convenient reading silently.

- **"revenue"** → GMV, net revenue (after refunds and discounts), or recognized revenue?
  Default to **net revenue** and say so in the answer.
- **"customer"** → `customer_id` (account) or `user_id` (person)? Counting `user_id`
  inflates B2B counts by roughly 1.7x.
- **"active"** → see `active_customers` in `metrics.md`; it is not "logged in".
- **"last week/month"** → the last *complete* calendar week or month, never trailing
  7/30 days.
- **Timezone** → `*_at` columns are UTC, `*_date` columns are already America/Sao_Paulo.
  Never mix the two in one filter.
- **Freshness** → anchor windows on `MAX(order_date)` in the table, not on
  `CURRENT_DATE`. Several tables settle late.

## Ground rules

- Try the metric layer (`metrics.md`) before any raw SQL, every time.
- Named segments exist for the populations people ask about — hand-rolling their `WHERE`
  clauses is the dominant wrong-answer mode here.
- Every domain doc owns a hygiene filter. Apply it.
- Answer with a provenance footer. Tier 3 (raw exploration) must be labelled as such.
