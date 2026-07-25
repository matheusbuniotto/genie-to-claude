# Data foundations

Source: [How Anthropic enables self-service data analytics with Claude](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude)

Targets: **entity ambiguity** (mainly) and the first line of defense against **staleness**.

Standard data eng practices (dimensional modeling, shift-left testing, freshness/completeness checks) still apply — this isn't a replacement, it's what agents make more urgent since the end user of the model is no longer a data expert who can sanity-check output.

## Practices that worked

- **Create canonical datasets.** Most failures = agent can't map a concept ("revenue for product X") to one table/column/definition because several plausible near-duplicates exist. Fix: curate a small set of owned, consumption-ready, discoverable canonical models; aggressively deprecate near-duplicates. Physical rollups/caches should derive mechanically from canonical models, not live alongside them as alternatives.
- **Enforce standards on three axes**: tooling (agent structurally routed to canonical models first), CI (bypassing changes fail review), mandate (teams must build on the governed layer or justify why not). Governance without enforcement decays back into "multiple candidates."
- **Colocate artifacts.** Modeling, semantic layer, reference docs, and canonical dashboard definitions live in one repo with CI checks protecting cross-layer integrity — a modeling change that breaks a downstream dashboard/metric gets flagged and fixed in the same PR.
- **Treat metadata as a first-class product.** Column/table descriptions, metric definitions, grain docs, valid value ranges, lineage, ownership, model tiering — maintained with the same rigor as the transformations themselves. This is what makes a warehouse "legible" the way a well-documented codebase is legible to a coding agent.
