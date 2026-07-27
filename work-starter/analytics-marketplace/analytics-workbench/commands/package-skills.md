---
description: Zip each domain's Skill folder (plus a router Skill built from INDEX.md) for upload to claude.ai / Claude Desktop — for business teams without a GitHub account or Claude Code.
argument-hint: [optional: one domain name to package alone]
allowed-tools: Bash, Read
---

Package the analytics Skills for claude.ai / Claude Desktop upload: **$ARGUMENTS**

Neither surface runs Claude Code plugins — no subagents, hooks, or Bash tool — but both
accept an uploaded Skill (a zip with the skill folder as its root, e.g. `orders/SKILL.md`)
under Settings → Capabilities, shared across the account. Every
`analytics/references/<domain>/` folder is already shaped that way.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/package_skills.py ${ARGUMENTS:+--domain "$ARGUMENTS"}
```

Run from the repo root. Writes to `dist/skills/` by default. Besides zipping, it:

- **Fixes the `name` field.** claude.ai validates it — lowercase letters, numbers and
  hyphens only, max 64 chars — which a human title like "Orders & Revenue" violates.
  Claude Code never enforces this (nothing there auto-loads `analytics/references/` as a
  real Skill), so this is the first point anything checks it. Rewritten to the domain
  slug at packaging time.
- **Builds a `warehouse-router` Skill from `INDEX.md`.** Inside Claude Code,
  `warehouse-knowledge` reads `INDEX.md` before opening any domain doc, so domains never
  compete for attention. Uploaded standalone, N domain Skills would compete on their own
  descriptions with nothing funnelling them — this router does that job on claude.ai /
  Desktop instead.

Report the zip files written, then this to whoever is sending them to the business team:

1. Upload every zip under **Settings → Capabilities → Skills**, on either claude.ai or
   Claude Desktop — they share an account, so one upload covers both.
2. **Confirm the Databricks MCP connector is enabled** for that account before relying on
   any domain Skill to actually query the warehouse. A Skill can route and state the
   hygiene filter; only the connector runs SQL. If a domain's `SKILL.md` doesn't yet name
   the connector, add a line referencing its fully-qualified tool name (`ServerName:tool`,
   e.g. `Databricks:query`) — Claude can fail to find an MCP tool referenced by a bare
   name once more than one server or Skill is loaded.
3. A flat catalog file (`metrics.md`-style — not a Skill folder) is **not** zipped. Paste
   its content into the router Skill's body, or upload it separately as its own Skill or
   project knowledge file, if the business team needs it.
