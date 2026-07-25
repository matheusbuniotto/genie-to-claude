# Why analytics agents fail

Source: [How Anthropic enables self-service data analytics with Claude](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude)

Analytics is not like coding for an agent. Coding is open-ended and rewards creativity, with tests/docs as guardrails. Analytics usually has **one correct answer from one correct source**, with no deterministic way to verify correctness after the fact.

Core problem: **mapping a user's question to the specific, up-to-date entity in the data model.** Solve that and the SQL becomes trivial.

## The three failure modes

1. **Concept <> entity ambiguity** — hundreds of plausible fields/tables could answer a question (e.g. "active users": which actions count as active? include fraud? what lookback window?).
2. **Data staleness** — schemas, sources, and business definitions change constantly; agent knowledge and docs rot and start giving subtly wrong answers.
3. **Retrieval failure** — the right info exists and is documented, but the search space is too large for the agent to find it.

Anthropic's whole agentic stack (data foundations, sources of truth, skills, validation) is organized to attack these three specifically — not to improve SQL generation.

Result at Anthropic: 95% of business analytics queries automated via Claude, ~95% aggregate accuracy.
