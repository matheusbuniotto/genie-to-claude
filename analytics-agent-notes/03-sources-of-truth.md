# Sources of truth

Source: [How Anthropic enables self-service data analytics with Claude](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude)

If data foundations are the warehouse itself, sources of truth are the reference surfaces an agent consults to navigate it. Targets **concept <> entity ambiguity** directly. Roughly descending order of trust:

1. **Semantic layer** — compiled metric/dimension definitions. Agent calls a function, gets one number, same number every surface produces. Structurally required as first resort.
   - *Didn't work*: auto-generating the semantic layer from raw tables/query logs via LLM — it encoded the same ambiguities it was meant to eliminate, net-negative vs. a smaller human-curated layer. **Generate documentation with Claude; keep definitions human-owned.**
2. **Lineage / transformation graph** — when the semantic layer doesn't cover a question, lineage + table ranking (by reference count) tells the agent which upstream models feed a concept, which are deprecated, which share grain. Also backs freshness/provenance signals used in online validation.
3. **Query corpus** — historical SQL from dashboards/notebooks/analyses. Intuitively high-value, but raw retrieval access to thousands of prior queries moved accuracy by *less than a point* in ablation. Unstructured retrieval doesn't map new questions to precedent. What works: distilling the corpus into structured per-domain reference docs and reusable patterns (i.e., turning it into skills), not handing the agent raw search access.
4. **Business context** — most-skipped, most-underrated layer. Without it the agent answers what was literally asked, not what was meant (which product "the Q2 launch" means, that two teams define a term differently, why the question is being asked). Fed via a company knowledge graph: indexed docs, roadmaps, decision logs, org structure.

Common failure across all four: **poor or stale documentation.** Claude can draft docs/descriptions and flag gaps in CI, but humans must own curation and correctness.
