---
description: Ask the data warehouse a question in plain language and get a reviewed, sourced answer.
argument-hint: [your question, e.g. how did revenue do last month?]
---

Answer this data question end to end: **$ARGUMENTS**

Follow the `warehouse-runbook` skill exactly — including the mandatory `sql-reviewer`
pass before any number is shown, and the provenance footer after it.

If the question is ambiguous, ask **one** round of clarifying questions first. If the
answer would be tier 3 (raw exploration), say plainly that it is unreviewed territory
and the number should be verified before it goes anywhere.
