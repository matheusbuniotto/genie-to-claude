# Reference index — read this before any query

The router for `warehouse-knowledge`. One row per domain doc. An unregistered doc is
invisible to the agent, so register it here the moment you create one.

## Domain map

| Domain | Doc | Use for | Do NOT use for |
|---|---|---|---|
| Example domain (delete once real domains exist) | [`example-domain.md`](example-domain.md) | shows the doc shape — copy it, don't ship it | anything real |

<!-- one row per real domain; a few dozen rows is the expected steady state -->

**Not documented yet**: everything you haven't added. Say plainly that a domain is **not
documented** — never improvise an answer from a neighbouring table.

## Disambiguate before querying

Load-bearing words that mean more than one thing in your business. Fill this in as you
find them — every stakeholder correction that turns on a word meaning two things belongs
here.

- **"revenue"** → gross, net, or recognized? State the default and say so in the answer.
- **"customer"** → account or person? Which id gives an accurate count?
- **"active"** → define it; it is almost never "logged in".
- **"last week/month"** → last *complete* calendar period, not trailing N days.
- **Timezone** → which columns are UTC, which are local. Never mix in one filter.
- **Freshness** → anchor on `MAX(date)` in the table, not on today's date.

## Ground rules

- Try the semantic layer / metric layer before any raw SQL, every time.
- Named segments exist for named populations — hand-rolling their `WHERE` clause is the
  dominant wrong-answer mode in most warehouses.
- Every domain doc owns a hygiene filter (test rows, internal accounts, soft-deletes...).
  Apply it.
- Answer with a provenance footer. Tier 3 (raw exploration) must be labelled as such.
