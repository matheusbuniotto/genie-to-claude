---
description: See what this agent can answer, in plain language — the documented domains, example questions, and what it will decline.
argument-hint: [optional: a topic you're wondering about]
---

Follow the `analytics-help` skill.

Read the router `INDEX.md` (`analytics/references/INDEX.md`, or the path `CLAUDE.md`
names) and show, in business language:

1. **What you can ask** — each documented domain in one line, with two example questions
   per domain, phrased the way a person would actually say them. No table names.
2. **What isn't documented** — the domains listed as missing. These get declined rather
   than guessed at, and that's deliberate.
3. **Words worth being specific about** — the terms the router flags as ambiguous here
   (revenue, customer, active, "last month"), with what happens if they're left vague.

If **$ARGUMENTS** names a topic, answer for that topic first: say whether it's covered,
which domain owns it, and give one question that would work.

Close with one line on how to read the footer that comes with every answer, and offer to
explain it in more detail. Keep the whole thing short enough to read in a chat window —
this is an orientation, not a manual.
