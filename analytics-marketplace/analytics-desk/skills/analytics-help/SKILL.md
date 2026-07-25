---
name: analytics-help
version: 0.1.0
description: "IF someone asks what they can ask the data agent, what a provenance footer means, whether a number can be trusted or forwarded, why they were asked a clarifying question, or why an answer was refused — THEN invoke this skill. DO NOT invoke to answer the data question itself; that is warehouse-runbook."
---

# Helping someone who can't check the answer

The person asking usually can't tell a right number from a plausible one. That is the
whole design constraint. Explain in their language, never in the warehouse's.

## What they can ask

Look at the router `INDEX.md` and name the **documented domains in business terms** —
"orders and revenue", "marketing spend and attribution" — not table names. Give two or
three example questions drawn from those docs, phrased the way a person would say them.

Then name what is *not* documented, plainly, and say those questions will be declined
rather than guessed at. A person who knows the boundary stops trusting answers outside it.

## Reading the footer

Every answer ends with one. Translate it on request:

| Field | What it means for them |
|---|---|
| **Source: semantic layer** | The company's official definition. This is the same number the dashboards show. |
| **Source: governed table** | Built from a reviewed table, but the metric was assembled for this question. Sound, worth a glance from the data team if it's going somewhere important. |
| **Source: raw exploration** | Nothing official covered this. Treat it as a first look — **verify before forwarding**. |
| **Freshness** | The most recent day of data. A number can be correct and still be missing this week. |
| **Owner** | The team to ask if it looks wrong. They own the definition, not the agent. |
| **Reviewed** | A second agent attacked the query before the number was shown. It catches mechanical errors, not a misunderstood question. |

If they ask "can I put this in a board deck?" — semantic layer plus a settled date range,
yes; anything labelled raw exploration, or a period that hasn't closed, gets a human
sign-off first. Say which one applies rather than answering in general.

## Why they got a question instead of an answer

Three legitimate reasons, worth naming so it doesn't read as evasion:

- **A word meant two things.** "Revenue" may be gross, net or recognised; "customer" may
  be an account or a person. Picking silently is how a confident wrong answer happens.
- **The period was ambiguous.** "Last month" means the last complete calendar month here,
  not the trailing 30 days — the two differ, so it gets confirmed.
- **It wasn't a data question.** Access requests, broken pipelines, "why did this change"
  root cause. Those go to the owning team; guessing would be worse than routing.

## Why an answer was declined

- **Undocumented domain** — no reference doc covers it, so any answer would be invented.
  Say which team could document it.
- **Restricted data** — the query comes back for them to run themselves; personal data
  never lands in a chat answer, a summary or a file.
- **No warehouse connection** — nothing was queried, so there is no number. An agent that
  describes what a query "would return" is the failure mode this refuses to perform.

## Asking a better question

Suggest, don't lecture. The three things that most change the answer: the **time period**,
the **population** (which customers, which channel, which market), and the **decision**
behind it — the last one is what turns a number into an answer. One sentence of context
beats a precise-sounding question with no context.

If a number looks wrong to them, that is a finding worth keeping: get the specific
objection ("that's not how we count active"), and tell them it should reach the domain
owner, who fixes the definition once for everyone rather than for this one thread.
