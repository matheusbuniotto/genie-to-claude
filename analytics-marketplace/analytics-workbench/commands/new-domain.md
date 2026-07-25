---
description: Document a new business domain — a reference doc written from the real tables, its router entry, and a starter eval set.
argument-hint: [domain name, e.g. marketing]
---

Bootstrap the `$ARGUMENTS` domain. Follow the `reference-doc` and `eval-loop` skills.

1. **Investigate before writing.** Inspect the actual tables for this domain: grain,
   row counts, date ranges, enum values, obvious exclusions. Read whatever dbt/SQL models
   and column comments exist in the repo. Do not write a doc from the table names alone.
2. **Draft `analytics/references/$ARGUMENTS.md`** using the skeleton. Every fact you
   could not verify goes in as `TODO`, never as a plausible guess — a confident wrong
   line in a reference doc is worse than no line.
3. **Register it** in `analytics/references/INDEX.md`: use-for, do-NOT-use-for, and any
   term this domain adds to the disambiguation list.
4. **Draft ~10 evals** in `analytics/evals/$ARGUMENTS.jsonl`: the questions stakeholders
   actually ask, one per known gotcha, and at least one that must escalate rather than
   answer (PII, out of scope). Grade on tables/filters/tier, never on numbers.
5. **Report the TODO count** and ask the domain owner to fill them. The domain is not
   ready to announce until TODOs are zero and its eval slice passes ~90%.

Metric definitions are the domain owner's to write, not yours. Draft the documentation,
mark the definitions `TODO`, and say so.
