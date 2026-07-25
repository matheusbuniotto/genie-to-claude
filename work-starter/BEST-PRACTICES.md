# Best practices

Distilled from Anthropic's internal experience running this pattern (95% of business
analytics automated, ~95% accuracy) plus what held up building the reference
implementation this starter is copied from. Organized by the three failure modes
everything here exists to prevent.

## Concept ↔ entity ambiguity — collapse it before the agent ever queries

- **One governed dataset per concept.** If "revenue" has three plausible tables, the
  agent will eventually pick the wrong one. Deprecate the near-duplicates aggressively —
  don't just add a fourth option.
- **Named segments over hand-rolled filters.** If "paying customer" or "active user" is
  asked about often, define it once and reference it. A `WHERE` clause reproducing a
  named segment by hand is the single most common wrong-answer mode in practice.
- **Semantic layer first, always.** Metric/metric-view before governed table before raw
  SQL. Don't drop a tier because a question "needs a join" or "needs a custom date
  window" — those are usually already handled by the layer above.
- **Resolve ambiguous words in the doc, not in the agent's head.** "Revenue", "customer",
  "active", "last month" — write down what they mean at your company. Every stakeholder
  argument about a number usually turns out to be two people meaning different things by
  the same word.

## Staleness — keep docs from rotting faster than the model improves

- **Same PR.** The change that alters a model's grain, filters, or columns is the same
  change that updates its reference doc. Anything else is a promise that doesn't hold.
  The bundled doc-drift hook nudges this; treat the nudge as a requirement, not a
  suggestion.
- **Humans own definitions; Claude drafts documentation.** Auto-generating metric
  definitions from raw tables and query logs tested *net-negative* — it produces
  plausible definitions that encode the exact ambiguity you're trying to remove. Use
  Claude to draft column descriptions and gotcha wording. Don't let it invent what
  "revenue" means.
- **Describe, don't prescribe.** Grain, scope, exclusions, join keys — these stay true.
  Step-by-step query recipes go stale and get copied wrong. Write the shape of the
  answer, not a fill-in-the-blanks query.
- **Prune.** Scaffolding written for a model generation that no longer trips on that
  failure is now just tokens between the agent and the real content. Delete it.

## Retrieval failure — make sure the agent finds what's already documented

- **A thin router, not a search problem.** `INDEX.md` narrows a warehouse with a million
  fields down to one file before a query is ever written. If the agent is reading the
  whole reference directory, the router has failed, not "been thorough."
- **Explicit routing triggers.** "IF the question is about X → use this. DO NOT use for
  Y" beats a paragraph of prose the agent has to infer routing from.
- **Don't expose the raw query corpus.** Giving an agent grep access to thousands of
  historical queries barely moves accuracy, even when the right answer is verifiably in
  there — the bottleneck is mapping a question to the right entity, not access to prior
  work. Distill the corpus into reference docs and reusable patterns instead.

## Validation — how you find out which failure mode is still leaking

- **Grade the query and the provenance tier, not the number.** Numbers move daily; a
  number-based assertion is wrong the moment the data lands. Assert on tables, filters,
  metric names, and whether the answer actually used the semantic layer.
- **Anchor the tier check to the footer, not to prose.** "The semantic layer doesn't
  cover this" should not read as *having used* the semantic layer. Grade the stated
  source, not a keyword mention.
- **A few dozen evals per domain is the ceiling**, not the floor to aim past. Diminishing
  returns set in fast, and the ceiling drops with every model generation. Calibrate by
  checking how well offline pass rate predicts what actually happens in production.
- **Two CI tiers.** A free structural gate (docs registered, evals well-formed, links
  resolve) on every PR; a token-costing eval run on demand or on eval-affecting changes.
  Collapsing them into one job means the cheap checks don't run often enough or the
  expensive ones get skipped to save money.
- **Store eval results as telemetry, not as a test log.** Model, doc version, tokens,
  pass/fail, timestamp — so "did that change help" is a query over history, not a memory
  of yesterday's run.
- **Ablate one variable at a time**, holding the eval set fixed. Record null results too
  — a stacked-refinement pass that made things worse is worth exactly as much as a win,
  and cheaper to write down than to re-discover.
- **Gate launches per domain**, not globally. A domain isn't announced to its
  stakeholders until its own eval slice clears ~90%. This forces the doc fixes before
  users hit the failure, not after.
- **Mandatory adversarial review before any number ships.** Costs roughly +30% tokens and
  +70% latency for a real accuracy gain. Never let the same agent that wrote the query
  self-certify it.
- **Every answer carries a provenance footer** — source tier, freshness, owner. It
  doesn't make the answer more correct; it tells the reader how much to verify before
  forwarding. "Raw exploration, freshness unknown" is a red flag by design.
- **Harvest corrections same-day.** Any stakeholder saying "wrong table" or "you missed
  the filter" is a free eval case and a one-line doc fix. The fix path should be boring —
  edit markdown, merge — or domain owners stop doing it.
- **The silent failure — wrong, plausible, unobjected-to — has no full fix.** Partial
  mitigations: the provenance footer, human sign-off on anything leadership-bound, and a
  standing eval that checks top KPIs against the blessed dashboard.

## When you're deciding how much of this to build

Ask, honestly:
- How much does a wrong answer cost you today vs. in six months? Model improvements
  shrink some of these problems for free — don't build permanent infrastructure around a
  gap that's closing on its own.
- How fast is the business changing? A simple, low-traffic warehouse doesn't need the
  full loop; a fast-changing one rots without it.
- Who's on the other end? Analysts who can smell a wrong number tolerate more risk than
  executives who can't.
- What's your risk tolerance for cost vs. accuracy? Adversarial review and a full eval
  suite both cost real money — know what you're buying before you build all of it.

If starting from zero: one governed dataset, a couple dozen evals, and the thin router
capture most of the upside. Everything else here is what you add once those hold.
