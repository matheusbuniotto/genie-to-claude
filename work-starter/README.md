# Analytics agent starter

Move an existing Genie space into Claude Code — as reference docs, skills and an eval
suite in your own repo.

Copy this folder into your work repo and follow the steps below. Everything in
`analytics-marketplace/` is generic and installs as-is; everything in `analytics/` is a
skeleton you fill with your warehouse's content.

```
analytics-marketplace/   the two plugins — install as-is, don't fork them
analytics/               your content: reference docs + evals (replace the example)
CLAUDE.md                the only environment-specific file — fill in the brackets
BEST-PRACTICES.md        read before your second domain
```

**Before you start:** Claude Code and the `databricks` CLI authenticated
(`databricks auth login`). No fixture or fake data ships here — this starter points at a
real workspace.

Everything below is a slash command. The plugins carry their own scripts and run them for
you; you never have to install anything Python-side or remember a flag.

---

## 1. Install the plugins

```shell
/plugin marketplace add ./analytics-marketplace
/plugin install analytics-desk@analytics-agents        # business users
/plugin install analytics-workbench@analytics-agents   # data team
/reload-plugins
```

Verify with `claude plugin details analytics-desk@analytics-agents` — 5 skills, 1 agent.
Same for `analytics-workbench` — 8 skills, 1 agent, 1 hook.

New to this? Ask Claude "how do I set this up?" — the `analytics-onboarding` skill walks
through the paths below and tells you what "done" means at each step.

## 2. Point it at your warehouse

Edit `CLAUDE.md` and fill in every bracket: how to connect, your default catalog and
schema, and whether you have a semantic layer. Nothing else in this folder encodes
anything about your environment.

## 3. Bring your Genie space over

```shell
/analytics-workbench:migrate-genie <space-id>
```

Tables, column synonyms, instructions, sample questions and benchmarks become
`analytics/references/<domain>.md` and `analytics/evals/<domain>.jsonl`.

No Genie space? Bootstrap from the tables instead — it inspects them before writing
anything, and marks what it couldn't verify as `TODO`:

```shell
/analytics-workbench:new-domain <name>
```

Either way, delete `analytics/references/example-domain.md`, its eval file and its
`INDEX.md` row once one real domain exists.

## 4. Close the TODOs — this is the actual work

A Genie space has no field for routing triggers, grain, exclusions, deprecated tables,
ownership or freshness, so the migrator writes `TODO` instead of guessing. The script
exiting 0 means the typing is done, not the migration.

Work them in this order: the routing trigger and the `INDEX.md` row (an unregistered doc
is invisible to the agent), then tier-1 metric coverage, then grain, exclusions, owner and
freshness. Ask the domain owner for what the warehouse can't tell you.

```
/analytics-workbench:check-setup
```

Free — no API calls, no warehouse. It fails until the doc is registered and the migrated
evals have real tiers and assertions, and tells you which. That red build is the gate;
don't silence it by deleting cases.

## 5. Prove the migration preserved the answers

Genie's benchmark SQL is the old system's answer. Run the slice with number parity on and
compare like for like:

```
/analytics-workbench:run-evals ^<domain>- parity
```

Every case with `gold_sql` has that SQL executed against your warehouse, and Claude's
answer must state the number it returned. Anchor each gold query to a fixed window first — "last month" gives a
different number next month and the comparison means nothing.

A case failing on `numbers_ok` alone — right table, right tier, wrong number — is the
finding that blocks the migration. Without this run you know Claude cited the right table;
you don't know it agreed with Genie.

**Don't announce a domain to stakeholders until its slice clears ~90%.**

## 6. Hand it to the business users

This is the part that matters — they're the ones who can't tell a right number from a
plausible one. Tell them two commands and one habit:

```
/analytics-desk:what-can-i-ask          # what's covered, in business language
/analytics-desk:ask what was net revenue last month?
```

Every answer ends with a provenance footer — source tier, freshness, owner — and has
passed through the `sql-reviewer` subagent before they see a number. **The habit: read the
footer before forwarding.** `semantic layer` is the official number; `raw exploration`
means nothing governed covered the question, so it needs a check first.

They don't have to learn any of that up front — the `analytics-help` skill explains the
footer, a clarifying question, or a declined answer whenever someone asks. Point them at
`/analytics-desk:what-can-i-ask` on day one and let the rest arrive when it's needed.

## 7. Keep it alive

Unmaintained, this decays fast: measured accuracy drifts from ~95% to ~65% in about a
month.

- `/analytics-workbench:review-analysis <analysis>` before anything reaches a stakeholder or a deck.
- The doc-drift hook nudges you when you edit a model a reference doc names. Update the
  doc in the same change, not later.
- Every correction ("wrong table", "you missed the fraud filter") becomes one line in the
  doc and one eval case, same day.
- [`BEST-PRACTICES.md`](BEST-PRACTICES.md) before your second domain, not your fifth.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| Agent answers without reading any doc | The doc isn't in `analytics/references/INDEX.md`. The router is the only way in. |
| `/analytics-workbench:check-setup` reports `unfinished migration` | Migrated eval cases still carry `expect_tier: TODO`. Set the tier and add assertions. |
| Answers have no provenance footer | Plugins aren't loaded — re-run `/reload-plugins` and verify the skill count. |
| `--gold-cmd` reports `gold_error` | The gold SQL no longer runs. That's a finding about the eval set; fix the query, don't drop the case. |
| Agent invents a table | It has no doc for that domain. Say the domain is undocumented rather than widening its access. |

The two plugins are the whole behavioural surface. If a skill references a path
(`analytics/references/...`), keep that convention; everything else — what "revenue" means
at your company, which tables are canonical — is content you own, not code to modify.
