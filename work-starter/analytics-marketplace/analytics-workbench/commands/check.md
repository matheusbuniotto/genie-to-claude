---
description: Structural gate — evals well-formed, docs registered in the router, links resolve, skeleton intact. No model calls, no credentials.
allowed-tools: Bash, Read, Edit, Glob, Grep
---

Run the cheap gate:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check.py
```

Run from the repo root. It costs nothing — no API calls, no warehouse — so it runs before
every commit and on every PR. It cannot tell you the agent is accurate; only
`/analytics-workbench:evals` does that. What it catches is the drift that precedes wrong
answers.

Then, for each failure, fix the cause rather than the symptom:

- **`unfinished migration`** — a migrated eval still carries `expect_tier: TODO`. Set the
  real tier and add assertions. Deleting the case is not closing it.
- **`has no assertions`** — a case that can never fail. Assert on the table, the hygiene
  filter, the metric name, or the tier.
- **`not registered in INDEX.md`** — the router is the only way in; an unregistered doc is
  invisible no matter how good it is. Add the row with its "use for" and "do NOT use for".
- **`missing section(s)`** — the doc is missing part of the skeleton. Write the section;
  if it genuinely isn't a domain doc (a metric catalogue, an index), mark it with the
  `<!-- not-a-domain-doc -->` opt-out instead.
- **`dangling link`** — fix the path, or delete the reference.

Report what you fixed and what you left, with the reason. If the run is clean, say so and
name what it does *not* prove: structure, not accuracy.
