# Roadmap

Direction: **everything a user does is a slash command.** The Python in `scripts/` is
implementation the plugin runs — nobody should have to install a runtime, remember a flag,
or read a script to use this.

## Next

1. **Multi-space router** — migrate every Genie space in one pass and generate the
   `INDEX.md` draft, flagging where two spaces claim the same tables or disagree about the
   same filter. Migrating one space at a time hides exactly the ambiguity the router exists
   to collapse.
2. **Shadow parity against the live space** — ask the same question of Genie and of Claude,
   compare the numbers, log the disagreements. Turns parity from a handful of migrated
   benchmarks into a continuous, per-domain cutover gate.
3. **Harvest conversation history** — real questions, the SQL that answered them, and any
   feedback signal, distilled into eval cases and one-line doc fixes. Distilled, not
   handed over raw: raw corpus retrieval measured under a point of accuracy.
4. **`/analytics-workbench:verify-schema`** — diff the tables and columns the docs name
   against `information_schema`. `check.py` proves docs are well-shaped and `seed.py`
   proves their numbers; nothing yet proves the entities still exist.
5. **Ablation and telemetry as commands** — `/analytics-workbench:ablate` for the
   before/after run the eval-loop skill currently describes by hand, and a summary over
   `results.jsonl` so "did that change help?" is a question you can ask.

## Later

- Runtime hybrid routing (Claude for migrated domains, live Genie for the rest). Useful
  mid-migration, but it gives one question two answer paths — only safe once (2) can show
  they agree.
- Enforce `Ownership` and `Freshness` in the structural gate. Breaking for existing docs,
  so it waits for a version bump.

## Not planned

A SQL dialect transpiler · LLM-generated metric definitions (measured net-negative:
they encode the ambiguity they were meant to remove) · raw grep access over the query
corpus · a multi-warehouse abstraction before there is a second warehouse.
