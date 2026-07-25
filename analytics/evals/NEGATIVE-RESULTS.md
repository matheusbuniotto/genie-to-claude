# What didn't work

One line per ablation that came back flat or negative, so nobody spends a week
rediscovering it. Cheap to append, and it compounds — a null result that redirects a
roadmap is worth more than a win.

Format: `date · what was tried · effect on the eval slice · what we concluded`

## Inherited from the source material

These are Anthropic's published results, not measured on this repo. Re-run them before
treating them as true here — but don't run them *first*.

- **Raw grep access to the whole SQL corpus** (thousands of dashboard, transformation and
  notebook files) · <1 point, either direction · The agent verifiably read the files, and
  the answer was present ~80% of the time it got a question wrong. Access was never the
  bottleneck; mapping a question to the right entity was. This is why the router exists
  and the query corpus is distilled into reference docs rather than exposed directly.
- **LLM-generated metric definitions** bootstrapped from raw tables and query logs ·
  net-negative vs a smaller human-curated layer · The definitions looked plausible and
  encoded the exact ambiguity they were meant to remove. Claude drafts the docs; a human
  owns the definition.
- **More rounds of doc refinement** past ~3 iterations · three consecutive net-negative
  runs · The docs got longer, not better. Length is not the lever.
- **Cheaper model for the adversarial reviewer** · lost most of the accuracy gain, no
  meaningful speedup · Review quality is the whole point of the review.

## Measured here

<!-- append yours: date · change · delta on which slice · conclusion -->

- **2026-07-25 · skills wired vs docs only, `orders` slice (10 cases), Sonnet against the
  fixture · both arms 0/10 · INVALID RUN — the eval set was broken, not the agent.**
  Every failure was `tier_ok`, and 8 of 19 cases demanded a `semantic layer` footer while
  `CLAUDE.md` simultaneously instructed the agent that no semantic layer existed here.
  Unpassable by construction. Fixed by making the tier real (`sem_orders` view in the
  fixture) rather than by weakening the assertion.
  **Method note worth keeping:** a suite where *every* case fails the *same* assertion is
  almost always a broken harness, not a broken agent. Check whether the assertion is
  satisfiable before reading anything into the score. This run cost ~$4 and produced no
  signal about skills — the ablation still needs re-running post-fix.
- **2026-07-25 · running the agent without the runbook skill · content assertions pass,
  `tier_ok` fails.** Docs alone get the agent to the right table and the right filter; the
  provenance footer only appears when the runbook skill is loaded. Consistent with the
  claim that skills carry the *procedural* half — but this is one case, not a measured
  pass rate.
- **2026-07-25 · same case with both plugins installed · PASS, 194s.** Routed to
  `sem_orders`, anchored the window on `MAX(order_date)`, disambiguated "revenue" per the
  router, spawned `sql-reviewer`, emitted the full footer. Latency is dominated by the
  adversarial review, in line with the ~+72% the article reports. n=1 — this shows the
  stack works, not how often it is right.

- **2026-07-25 · skills ablation, 4 discriminating cases, Sonnet, fixture warehouse ·
  1/4 (25%) without skills → 3/4 (75%) with · directionally matches the article's
  21% → >95%.** Arms differ only by `claude plugin disable/enable analytics-desk`.
  Without skills the agent got the *content* right (no missing assertions on 001/007) but
  never emitted a provenance footer, and on 003 it reached for the deprecated `orders_v1`.
  With skills it hit the footer every time and avoided the deprecated table.
  **n=4, single run per case — a direction, not a rate.** Read it as "the footer and the
  deprecation routing come from the skills", not as a 50-point accuracy claim.

## Worth knowing

`claude plugin eval <plugin> --ablation with-without` runs the with/without-skills
experiment natively, with `--max-cost-usd` as a budget ceiling and `--runs` for
repetition. It was in early access and unavailable when this repo was built, so
`scripts/run_evals.py` does the job instead. If it has shipped by the time you read this,
prefer it for ablations and keep `run_evals.py` for the fixture-graded telemetry rows.
