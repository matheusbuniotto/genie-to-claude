---
description: Review a finished analysis before it reaches a stakeholder — method, query, claims, provenance, and the missing doc line behind any finding.
argument-hint: [a file, a query, or a description of the analysis]
---

QA this analysis: **$ARGUMENTS**

If the argument is a file or notebook, read it. If it's a query, read the reference doc
for the domain it touches first. If nothing was given, QA the analysis in the current
conversation.

Spawn the `analysis-reviewer` agent and report its verdict verbatim — do not soften it and do
not fix things silently.

Then, for each `DOC GAP` it reports:
1. Draft the one-line fix for the owning `analytics/references/*.md`.
2. Draft the eval case for `analytics/evals/<domain>.jsonl` that would have caught it.
3. Show both and ask before writing. A finding fixed only in this analysis recurs next
   week.
