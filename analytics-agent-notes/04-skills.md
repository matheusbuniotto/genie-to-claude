# Skills

Source: [How Anthropic enables self-service data analytics with Claude](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude)

If sources of truth are *declarative* knowledge (what a metric means), a skill is *procedural* knowledge (which sources to consult, in what order, what a finished analysis looks like). Targets **retrieval failure**.

A Claude Code [skill](https://code.claude.com/docs/en/skills) is a folder of markdown read on demand.

**Impact measured**: without skills, accuracy on evals didn't exceed 21%. With skills: consistently >95%, ~99% in some domains.

## Best practices

- **Pairwise skills**:
  - *Knowledge* skill = thin top-level router. "Try the semantic layer first; if no coverage, here are ~30 reference files for this domain." Narrows a million-field warehouse down to a few dozen curated files before any query is written — this is the direct fix for retrieval failure.
  - *Runbook* skill = the process a senior analyst follows: clarify the question → find sources via the knowledge skill → run the query → loop through adversarial review sub-agents. Bundles reusable analysis patterns (retention curves, rate decomposition, funnel analysis) so common requests aren't reinvented.
- **Proper reference docs**, written for LLM retrieval: describe tables (grain, scope, exclusions), gotcha mechanics ("exclude known free-email domains, but keep custom ones"), explicit routing triggers ("IF question is about experiment lift... DO NOT use for raw event counts"). Avoid prescriptive recipes — they go stale.
- **Treat skill maintenance as first-class.** Offline accuracy drifted from ~95% at launch to ~65% over a month without active upkeep. Fix: colocate skill markdown in the same repo as transformation models, so the PR that changes a model also updates its doc. A code-review hook flags reporting-model changes missing a skill update (~90% of data-model PRs now include one). Regularly prune scaffolding as models improve.
- **One canonical answer across every surface** (Slack, IDE, dashboard tool, standalone agent). Achieved via one canonical source repo, auto-synced to: plugin marketplace (IDE), cloud-storage blobs (hosted apps), and MCP resources. Avoid hardcoded repo paths / surface-specific namespaces from the start.

## Reference doc skeleton

```
# [Domain] Tables

## Quick Reference
### Business Context — [what this domain means in plain words]
### Entity Grain — [what one row represents]
### Standard Hygiene Filter — [the filter every query in this domain applies]

## Dimensions
- [How key dimensions are encoded, and how the same concept is named differently across tables]

## Key Tables
### [table_name]
- Grain: [...] · Scope/exclusions: [...]
- Usage: [when to use it, when NOT to, join keys, required filters]

## Gotchas
- [Wrong-answer modes a senior analyst would warn you about]

## Best Practices / Common Query Patterns
- [Default choices, standard cuts, worked patterns]

## Cross-References
- [Neighboring domain docs that own adjacent questions]
```
