# Example Domain Tables

**This is a template, not real content.** Copy this file to `<your_domain>.md`, fill in
every bracket, delete this file, and remove its row from `INDEX.md`. The section headers
below are load-bearing — `scripts/check.py` checks a real domain doc for them.

## Quick Reference

### Business Context
[What this domain means in plain words, and what's explicitly out of scope. Two sentences.]

### Entity Grain
[What one row of the primary table represents. Name the trap if summing at a different
grain gives a different number — e.g. "line items exclude shipping".]

### Standard Hygiene Filter
```sql
WHERE [the filter every query in this domain applies]
```
[What breaks without it, quantified if you can measure it — "omitting this overstates
totals by ~5%" makes an agent take it seriously; "don't forget this" doesn't.]

### Ownership & Freshness
- **Owner**: [the owning team, not a person]
- **Refresh cadence / lag**: [...] · **Settles late?**: [e.g. "the trailing 14 days are
  provisional"]

[The provenance footer prints an owner and a freshness on every answer; this is where the
agent reads them from.]

## Metrics (tier 1 — required first resort)

- [The metric view or semantic-layer entry covering this domain, its measures, dimensions
  and named segments. Hand-rolling a `WHERE` clause that reproduces a named segment is the
  dominant wrong-answer mode.]
- [If no metric view covers this domain, say that explicitly — an agent must know tier 2
  is the top of the ladder here, not that tier 1 was left out.]

## Dimensions

- [How key dimensions are encoded, and where the same concept is named differently across
  tables — e.g. `channel_code` here vs `channel_name` in a neighbouring domain.]

## Key Tables

### `catalog.schema.table_name`
- **Grain**: [...] · **Scope/exclusions**: [...]
- **Usage**: [when to use it, when NOT to, join keys, required filters]
[... one section per governed table; mark deprecated ones as deprecated, don't delete
    the entry — an agent needs to know NOT to use it, not just fail to find it ...]

## Blessed Dashboards

- [The governed dashboard that already publishes each common number here, and its owning
  team. A query that disagrees with the dashboard a stakeholder already reads is a
  finding, not a result — reconcile before reporting.]

## Gotchas

- [The wrong-answer modes a senior analyst would warn you about. Name the mechanism, not
  just the rule: "X is already net of Y — subtracting Y again double-counts" beats
  "don't subtract Y".]

## Best Practices / Common Query Patterns

- [Default cuts, standard windows, patterns where the exact query form is the hard part.]

## Cross-References

- [Neighbouring domain docs that own adjacent questions, and why a question routes there
  instead of here.]
