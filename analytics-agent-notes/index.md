# Anthropic's self-service analytics agent stack — notes

Distilled from: [How Anthropic enables self-service data analytics with Claude](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude) 

Anthropic automates 95% of its internal business-analytics queries via Claude at ~95% accuracy. The core claim: analytics accuracy is a context/retrieval problem, not a code-generation problem — solve *entity ambiguity*, *staleness*, and *retrieval failure*, and correct SQL follows almost for free.

## Topics

1. [Failure modes](01-failure-modes.md) — why analytics agents fail differently than coding agents; the three root causes everything else here addresses.
2. [Data foundations](02-data-foundations.md) — canonical datasets, enforcement (tooling/CI/mandate), colocation, metadata as a first-class product.
3. [Sources of truth](03-sources-of-truth.md) — semantic layer, lineage graph, query corpus, business context, ranked by trust.
4. [Skills](04-skills.md) — knowledge/runbook skill pairing, reference-doc skeleton, cross-surface consistency.
5. [Validation](05-validation.md) — offline evals, ablation methodology, online monitoring, the unsolved "silent failure" mode.
6. [Getting started](06-getting-started.md) — minimum viable setup, questions to align on before over-building, full warehouse-skill skeleton.

## Reading order

New to this: 1 → 2 → 3 → 4 → 5 → 6.
Just want to bootstrap something: skip to 6, then 4.
