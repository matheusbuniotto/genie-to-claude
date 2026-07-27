# genie-to-claude

[![analytics](https://github.com/matheusbuniotto/genie-to-claude/actions/workflows/analytics.yml/badge.svg)](https://github.com/matheusbuniotto/genie-to-claude/actions/workflows/analytics.yml)

Move freely from Genie agents to Claude — and prove the answers survived the move.

This repo converts an existing Genie space into reference docs, skills and an eval suite
for Claude Code, plus the harness that checks Claude returns the same numbers Genie did.

## Quickstart

Install straight from this repo — no clone, nothing to build. Run these in Claude Code,
from whichever repo your analytics content lives in.

**1. Add the marketplace and install the plugins.**

```shell
/plugin marketplace add matheusbuniotto/genie-to-claude
/plugin install analytics-desk@analytics-agents        # business users
/plugin install analytics-workbench@analytics-agents   # data team
/reload-plugins
```

**2. Bring your Genie space over.**

```
/analytics-workbench:migrate-genie <space-id>
```

Its tables, synonyms, instructions and benchmarks become a reference doc and an eval set,
plus a count of the `TODO`s a human still owes — grain, ownership, freshness and the rest
a Genie space has no field for. The command walks you through closing them.

**3. Ask a question.**

```
/analytics-desk:what-can-i-ask                        # start here if you're new
/analytics-desk:ask what was net revenue last month?
```

Every answer routes to the semantic layer first, goes through a hostile reviewer, and
closes with a provenance footer saying how much to trust it.

New here? Just ask *"how do I set this up?"* — the `analytics-onboarding` skill takes it
from there.

### Want to see it work before pointing it at real data?

Clone this repo and the same commands run offline against a seeded SQLite warehouse — no
Databricks account, no credentials:

```bash
git clone https://github.com/matheusbuniotto/genie-to-claude && cd genie-to-claude
```

```
/analytics-workbench:migrate-genie analytics/examples/orders.serialized_space.json
/analytics-desk:ask what was net revenue last month?
```

The example is the real `serialized_space` v2 payload the Databricks API returns, and the
agent seeds the fixture warehouse itself if it's missing.

**Going to production →** [`work-starter/`](work-starter/README.md) is a self-contained
folder to drop into a work repo: an empty content skeleton and seven steps.

## Cheatsheet

| Command | Plugin | What it does |
|---|---|---|
| `/analytics-workbench:migrate-genie <space-id\|url\|file>` | workbench | Genie space → reference doc + eval set + counted `TODO`s |
| `/analytics-workbench:new-domain <name>` | workbench | bootstrap a hand-authored domain from the real tables, no Genie involved |
| `/analytics-workbench:check-setup` | workbench | free repo-invariant gate: router registered, evals well-formed, links resolve |
| `/analytics-workbench:run-evals [slice] [parity]` | workbench | grade the agent against the eval set; add `parity` to check the *numbers* |
| `/analytics-workbench:review-analysis <target>` | workbench | adversarial QA of a finished analysis; reports `DOC GAP`s to fix |
| `/analytics-workbench:package-skills [domain]` | workbench | zip domain Skills (+ a router) for claude.ai / Claude Desktop upload |
| `/analytics-desk:ask <question>` | desk | ask the warehouse; tier-routed, adversarially reviewed, provenance-footed |
| `/analytics-desk:what-can-i-ask` | desk | list documented domains and what the agent will decline, in plain language |

**The loop, in order:** migrate-genie (or new-domain) → close TODOs → check-setup →
run-evals (add `parity` right after a migration) → ask, or package-skills to hand it off.

## How to share this with a team

Two audiences, two mechanisms — don't force one into the other.

**A team with Claude Code and GitHub access.** Reference docs are **project-owned
files**, not plugin content — `analytics/references/` lives in *your* repo next to the
models it describes, so sharing it is exactly as hard as sharing any other file: commit
it, PR it. If one team authors for several consuming repos, have each consuming repo
pull the folder via a git submodule or subtree pinned to a commit, and bump the pin like
any other dependency update. Neither plugin needs reinstalling — only the content
underneath changes.

**A team on claude.ai / Claude Desktop only — no GitHub, no Claude Code.**

```
/analytics-workbench:package-skills
```

Zips every domain into an upload-ready Skill (`orders.zip`, `marketing.zip`, ...) plus a
`warehouse-router.zip` built from `INDEX.md`, so multiple uploaded Skills still funnel
through one router instead of competing on their own descriptions the way domains
normally would with nothing like `warehouse-knowledge` to fence them. Send the zips to
the business team; each gets uploaded once under **Settings → Capabilities → Skills** —
claude.ai and Claude Desktop share an account, so one upload covers both surfaces.

This carries over the routing knowledge (hygiene filter, tier, gotchas) but not
`analytics-desk`'s adversarial `sql-reviewer` or provenance footer, since those need
Claude Code's subagents and neither surface runs them. If a domain needs to actually
query the warehouse from claude.ai/Desktop, confirm an MCP connector (e.g. Databricks) is
enabled on that account first — a Skill can route and state the hygiene filter; only the
connector runs SQL.

## The migration, end to end

| Step | Command | What you get |
|---|---|---|
| 1. Export | `databricks api get /api/2.0/genie/spaces/$ID?include_serialized_space=true` | the raw space |
| 2. Convert | `/analytics-workbench:migrate-genie <id>` | a reference doc + an eval set, with `TODO` wherever Genie has no field |
| 3. Close TODOs | — | grain, exclusions, ownership, freshness, routing triggers: **the actual work** |
| 4. Prove parity | `/analytics-workbench:run-evals ^<domain>- parity` | Genie's benchmark SQL executed, Claude's answer compared against its number |

Step 3 is the point. The migrator refuses to guess: a Genie space has no notion of grain,
scope, deprecated tables, owner or freshness, so those come out as counted `TODO`s rather
than confident fabrications. The script is the typing; the TODOs are the migration.

Step 4 is what makes it defensible. Ordinary evals grade the query and the provenance
tier — deliberately, so they don't rot when the data moves. A migration is the exception:
the old system's number is the thing you promised to preserve, so `--gold-cmd` executes
the gold SQL and asserts the agent's answer states it. A case that passes every other
assertion but fails on `numbers_ok` — right table, right tier, wrong number — is exactly
the silent failure nothing else in the suite can see.

## Why any of this shape

Built on [*How Anthropic enables self-service data analytics with
Claude*](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude)
(distilled notes: [`analytics-agent-notes/`](analytics-agent-notes/index.md)). Its
premise: **analytics accuracy is a context and retrieval problem, not a code-generation
problem.** Map the question to the right entity and the SQL is trivial. Three failure
modes account for most wrong answers, and every directory here attacks one.

| Failure mode | What addresses it |
|---|---|
| Concept ↔ entity ambiguity | one governed definition per concept (`analytics/references/metrics.md`), named segments instead of hand-rolled `WHERE` clauses |
| Retrieval failure | a thin router (`analytics/references/INDEX.md`) that narrows the warehouse to one doc before any SQL is written |
| Staleness | evals, a doc-drift hook, and a seed script that asserts the docs are still true |

Without skills, measured accuracy on analytics questions sat at 21%; with them, above 95%.
That gap is why the migration target is a skill and a doc, not a prompt.

## Repo structure

One split runs through the whole repo: **plugins are the behaviour, `analytics/` is the
knowledge.** The behaviour is generic and stable — it never mentions your tables. The
knowledge changes daily and lives next to the models it describes. You install the first
and own the second.

```
.claude-plugin/marketplace.json    what /plugin marketplace add reads

analytics-marketplace/             ← the behaviour: install it, don't fork it
  analytics-desk/                  for people who can't check the answer
    skills/                        warehouse-knowledge (router), warehouse-runbook
                                   (process), analytics-help (explains itself)
    agents/sql-reviewer            hostile review, mandatory before any number ships
    commands/                      ask, what-can-i-ask
  analytics-workbench/             for the people who own the data
    skills/                        reference-doc, eval-loop, analytics-onboarding
    agents/analysis-reviewer       reviews a finished analysis, not just its SQL
    commands/                      migrate-genie, new-domain, check-setup,
                                   run-evals, review-analysis, package-skills
    scripts/                       what the commands run (check, evals, migrator, packager)
    hooks/                         flags a model change whose doc wasn't touched

analytics/                         ← the knowledge: this is the part you replace
  references/INDEX.md              the router — read before any query
  references/<domain>/SKILL.md     one skill per business domain (Claude-Skill-shaped)
  references/<domain>/reference.md that domain's deep detail, loaded only on demand
  evals/*.jsonl                    offline evals, graded on the query and the tier
  fixtures/seed.py                 builds the demo warehouse, asserts the docs are true
  examples/                        sample Genie spaces + what the migrator makes of them

work-starter/                      copy this folder into a work repo to start clean
analytics-agent-notes/             the research this is built on
.github/workflows/                 CI: rebuild fixture, verify doc claims, run selftests
```

Three consequences worth knowing up front:

- **The plugins never hardcode your warehouse.** `analytics/references/` is a default that
  `CLAUDE.md` can override; the connection ladder lives in `CLAUDE.md` too. Nothing in
  `analytics-marketplace/` needs editing to work against your data.
- **`analytics/` here is a worked example, not a library.** A fictional marketplace —
  orders, revenue, refunds — filled in properly so you can copy the shape. Replace it.
- **The router is the load-bearing file.** `references/INDEX.md` is how a question gets
  narrowed to one doc before any SQL is written. A doc that isn't registered there is
  invisible to the agent no matter how good it is.

## The two plugins

Installed in the quickstart above. Measured with `claude plugin details`:

| Plugin | Skills | Agents | Hooks | Always-on cost |
|---|---|---|---|---|
| analytics-desk | 5 | 1 | 0 | ~496 tok |
| analytics-workbench | 8 | 1 | 1 | ~707 tok |

~1,200 tokens of always-on context buys the router, the runbook, both reviewers, the
two self-explanation surfaces and every command; the reference docs load on demand, which is the entire point of the
router.

**analytics-desk** — for people who can't check the answer, which is the case the whole
design is built around. Routes to the semantic layer first, spawns a hostile `sql-reviewer`
before showing any number, and ends every answer with a provenance footer (source tier,
freshness, owner). It also explains itself: `/analytics-desk:what-can-i-ask` lists the
documented domains in business language and names what it will decline, and the
`analytics-help` skill translates the footer, the clarifying questions and the refusals —
a trust signal nobody can read is decoration.

**analytics-workbench** — for the people who own the data. Migrate Genie spaces, author
reference docs, QA a finished analysis, run and ablate the eval suite. Details in
[`analytics-marketplace/README.md`](analytics-marketplace/README.md).

## What makes this more than a template

- **The fixture warehouse asserts the docs are true.** Every numeric claim in a domain's
  `SKILL.md` or `reference.md` — "the hygiene filter is worth ~5% of GMV", "attributed
  revenue runs ~20% low" — is checked against seeded data on every build. Doc rot becomes
  a failing test.
- **Every gotcha is physically reproducible.** Skip the hygiene filter and GMV overstates
  by 5.1%; answer revenue from `fact_attributed_revenue` and it understates by 19.7%;
  count `user_id` and you get 666 customers instead of 400.
- **Migration output is compared before/after.**
  [`analytics/examples/migrated/`](analytics/README.md) is what the migrator produced;
  `analytics/references/orders/SKILL.md` is the hand-finished version. The gap between
  them is the human work a migration needs, in full view.

## Honest status

**Verified end to end.** Both plugins install and load with every component registered.
With them installed, `orders-001` passes against the fixture: the agent routes to
`sem_orders` (tier 1), resolves "last month" to the last *complete* calendar month by
anchoring on `MAX(order_date)`, disambiguates "revenue" as net per the router, spawns
`sql-reviewer`, and closes with a full provenance footer. 194s per case — the adversarial
review is most of it, matching the ~+72% latency the article reports.

Also verified: the fixture seeds and validates every doc claim; the migrator handles all
three Genie input shapes including the real `serialized_space` v2 API schema; number
parity passes and fails correctly against the fixture on migrated gold SQL; the CI `check`
job passes. Every script has a `--selftest`.

**Skills ablation, measured small:** 4 discriminating cases, arms differing only by
`claude plugin disable/enable` — **1/4 without skills, 3/4 with**. Directionally matches
the article's 21% → >95%, but n=4 with one run per case is a direction, not a rate. The
docs alone got the agent to the right table; the skills supplied the provenance footer and
the deprecated-table routing. See
[`analytics/evals/NEGATIVE-RESULTS.md`](analytics/evals/NEGATIVE-RESULTS.md), which also
records one invalid run worth learning from.

**Known limits.** `--gold-cmd` strips three-part names so gold SQL runs against the
offline fixture and rewrites `DATE '…'` literals; it is not a dialect translator. Parity
compares numbers as written, at 0.5% tolerance, matching rates at either scale — it will
not recognise "1.2M" as 1,234,567.

## Start here

Migrating a Genie space → [`work-starter/README.md`](work-starter/README.md).
What's coming → [`ROADMAP.md`](ROADMAP.md).
New to the ideas → [`analytics-agent-notes/index.md`](analytics-agent-notes/index.md).
Building content for your warehouse → [`analytics/README.md`](analytics/README.md).
Plugin internals → [`analytics-marketplace/README.md`](analytics-marketplace/README.md).
