#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Convert a Databricks Genie space into a knowledge-skill reference doc + eval set.

    uv run migrate_genie.py space.yml --domain orders
    uv run migrate_genie.py databricks.yml --space orders_space --domain orders
    databricks api get /api/2.0/genie/spaces/$ID?include_serialized_space=true \
      | uv run migrate_genie.py - --domain orders
    uv run migrate_genie.py --selftest

Writes analytics/references/<domain>.md and analytics/evals/<domain>.jsonl by default.

Accepts YAML or JSON, in any of the shapes Genie exports have used (serialized space,
bundle .geniespace.json, or a space wrapped in a `serialized_space` key). Everything it
cannot infer is emitted as a TODO in the output — a Genie space has no notion of grain,
exclusions, or ownership, and guessing them is how you get a confident wrong answer.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

TABLE_RE = re.compile(r"`?([a-z_]\w*)`?\.`?([a-z_]\w*)`?\.`?([a-z_]\w*)`?", re.I)


# --- parsing: tolerate every export shape ------------------------------------------


def load(raw: str, base: Path | None = None, space: str | None = None) -> dict:
    """Unwrap whichever Genie shape this is down to the serialized space.

    Handles: a bare serialized space; a `serialized_space` wrapper (string or mapping);
    and a bundle `databricks.yml` with `resources.genie_spaces.<key>`, following its
    `file_path` relative to `base` when the definition lives in a sidecar file.
    """
    doc = yaml.safe_load(raw)  # YAML is a superset of JSON, so one loader covers both
    if not isinstance(doc, dict):
        raise SystemExit("expected a mapping at the top level")

    spaces = (doc.get("resources") or {}).get("genie_spaces") or {}
    if spaces:
        if space and space not in spaces:
            raise SystemExit(
                f"space '{space}' not in bundle; found: {', '.join(spaces)}"
            )
        key = space or next(iter(spaces))
        if len(spaces) > 1 and not space:
            print(
                f"bundle defines {len(spaces)} spaces, using '{key}' "
                f"(--space to pick another)",
                file=sys.stderr,
            )
        resource = spaces[key] or {}
        if resource.get("file_path"):
            path = Path(resource["file_path"])
            if not path.is_absolute() and base:
                path = base / path
            inner = load(path.read_text(), path.parent)
            # the bundle resource owns the title; the sidecar rarely repeats it
            inner.setdefault("config", {}).setdefault(
                "name", resource.get("title") or resource.get("display_name") or key
            )
            return inner
        doc = resource

    for key in ("serialized_space", "space", "genie_space"):
        if isinstance(doc.get(key), (str, dict)):
            inner = doc[key]
            inner = yaml.safe_load(inner) if isinstance(inner, str) else inner
            # the live API's title/description sit beside serialized_space, not in it
            if isinstance(inner, dict):
                cfg = inner.setdefault("config", {})
                if isinstance(cfg, dict):
                    cfg.setdefault("name", doc.get("title") or doc.get("display_name"))
                    cfg.setdefault("description", doc.get("description"))
            doc = inner
    return doc


def text(value) -> str:
    """Genie's v2 schema wraps nearly every scalar in a list: descriptions, instruction
    content, questions and SQL all arrive as ["..."]. Older exports use plain strings.
    Flatten both to one string."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(text(v) for v in value if v is not None)
    return str(value)


def space_meta(doc: dict) -> tuple[str, str]:
    cfg = doc.get("config", doc)
    name = text(
        cfg.get("name") or cfg.get("display_name") or cfg.get("title") or "untitled"
    )
    return name, text(cfg.get("description"))


def tables(doc: dict) -> list[dict]:
    src = doc.get("data_sources", doc)
    if isinstance(src, list):  # some exports put the table list directly on the key
        src = {"tables": src}
    out = []
    for item in src.get("tables") or doc.get("table_identifiers") or []:
        if isinstance(item, str):
            out.append({"identifier": item})
            continue
        cols = []
        for col in item.get("column_configs") or []:
            cols.append(
                {
                    # v2 spells it column_name; the bundle examples use name
                    "name": col.get("column_name") or col.get("name"),
                    "synonyms": col.get("synonyms") or [],
                    "description": text(col.get("description")),
                }
            )
        out.append(
            {
                **item,
                "description": text(item.get("description")),
                "column_configs": cols,
            }
        )
    for mv in src.get("metric_views") or []:
        out.append(
            {**mv, "description": text(mv.get("description")), "_metric_view": True}
        )
    return out


def split_rules(body: str) -> list[str]:
    """One bullet per rule. Genie free-text is hand-wrapped, so a line following one
    that didn't end a sentence is a continuation, not a new rule — unless the line is
    itself a markdown bullet, which always starts a new rule regardless of punctuation."""
    rules: list[str] = []
    for line in str(body).splitlines():
        line = line.strip()
        if not line:
            continue
        is_bullet = line.startswith(("* ", "- ", "• "))
        if is_bullet:
            line = line[2:].strip()
        if is_bullet or not rules or rules[-1].endswith((".", "!", "?", ":")):
            rules.append(line)
        else:
            rules[-1] = f"{rules[-1]} {line}"
    return rules


def instructions(doc: dict) -> tuple[list[str], list[dict]]:
    """Returns (free-text rules, structured snippets)."""
    ins = doc.get("instructions", [])
    rules, snippets = [], []
    if isinstance(ins, str):
        rules = split_rules(ins)
    elif isinstance(ins, dict):
        # v2: text_instructions[].content (arrays). Older/bundle: a single `text` blob.
        for item in ins.get("text_instructions") or []:
            body = (
                item
                if isinstance(item, str)
                else text(
                    item.get("content") or item.get("instruction") or item.get("text")
                )
            )
            rules += split_rules(body)
        rules += split_rules(text(ins.get("text")))
        snippets = ins.get("sql_snippets") or []
        for fn in ins.get("sql_functions") or []:
            name = (
                fn
                if isinstance(fn, str)
                else text(fn.get("function_name") or fn.get("name"))
            )
            rules.append(f"SQL function available: {name}")
    elif isinstance(ins, list):
        for item in ins:
            if isinstance(item, str):
                rules.append(item)
            else:
                body = text(
                    item.get("instruction") or item.get("content") or item.get("text")
                )
                title = text(item.get("title") or item.get("display_name"))
                rules.append(f"{title}: {body}" if title else body)
    return rules, snippets


def benchmarks(doc: dict) -> list[tuple[str, str]]:
    """(question, gold SQL) pairs; SQL may be empty for sample questions."""
    out = []
    # v2 calls these example_question_sqls with flat question/sql arrays; the bundle
    # examples call them benchmarks with a nested answer[].content.
    ins = doc.get("instructions")
    examples = (ins.get("example_question_sqls") or []) if isinstance(ins, dict) else []
    for ex in examples:
        out.append((text(ex.get("question")), text(ex.get("sql"))))
    raw_benchmarks = doc.get("benchmarks") or []
    if isinstance(raw_benchmarks, dict):  # v2 wraps the list under "questions"
        raw_benchmarks = raw_benchmarks.get("questions") or []
    for bench in raw_benchmarks:
        sql = ""
        for answer in bench.get("answer") or []:
            sql = text(answer.get("content"))
            if sql:
                break
        out.append((text(bench.get("question")), sql))
    cfg = doc.get("config", doc)
    for question in cfg.get("sample_questions") or []:
        q = question if isinstance(question, str) else text(question.get("question"))
        if q and not any(q == existing for existing, _ in out):
            out.append((q, ""))
    return out


# --- emitting -----------------------------------------------------------------------


def reference_doc(domain: str, name: str, desc: str, tbls, rules, snippets) -> str:
    L = [
        f"# {name} Tables",
        "",
        "<!-- migrated from a Genie space by migrate_genie.py.",
        "     TODO markers are what Genie has no field for — a human fills them in. -->",
        "",
        "## Quick Reference",
        "",
        "### Use For / Do NOT Use For",
        "TODO: the routing trigger — 'IF the question is about X → use this doc. DO NOT",
        "use for Y (→ other-domain.md).' Without it the router can't tell this doc apart",
        "from its neighbours, which is the retrieval failure this doc exists to prevent.",
        "",
        "### Business Context",
        desc or "TODO: what this domain means in plain words.",
        "",
        "### Entity Grain",
        "TODO: what one row of the primary table represents.",
        "",
    ]

    hygiene = next(
        (s for s in snippets if "filter" in str(s.get("display_name", "")).lower()),
        None,
    )
    L += ["### Standard Hygiene Filter"]
    if hygiene:
        L += ["```sql", f"WHERE {hygiene.get('sql', '')}", "```"]
    else:
        L += [
            "TODO: the filter every query in this domain applies (test rows, fraud,",
            "internal accounts). Genie spaces usually bury this in free-text instructions —",
            "check the Gotchas below.",
        ]
    L += [
        "",
        "### Ownership & Freshness",
        "- **Owner**: TODO (ask a human — no Genie field carries this)",
        "- **Refresh cadence / lag**: TODO · **Settles late?**: TODO",
        "",
        "<!-- the runbook's provenance footer prints Owner and Freshness verbatim; while",
        "     these say TODO, every answer from this domain ships unattributed. -->",
        "",
    ]

    # Always emitted, even with nothing to put in it: tier 1 is the required first resort,
    # and a doc that silently omits the section teaches the agent to start at tier 2.
    metric_views = [t for t in tbls if t.get("_metric_view")]
    L += ["## Metrics (tier 1 — required first resort)", ""]
    for mv in metric_views:
        L += [
            f"### `{mv.get('identifier', '?')}`",
            f"- **Measures**: {', '.join(mv.get('measures') or []) or 'TODO'}",
            f"- **Dimensions**: {', '.join(mv.get('dimensions') or []) or 'TODO'}",
            "- **Named segments**: TODO (hand-rolling a WHERE clause that reproduces one",
            "  is the dominant wrong-answer mode)",
            "- **Owner**: TODO",
            "",
        ]
    if not metric_views:
        L += [
            "TODO: this Genie space exposes no metric view. Does a semantic layer cover",
            "this domain? If yes, document its measures, dimensions and named segments",
            "here and route to it first. If no, say so explicitly — the agent must know",
            "that tier 2 is the top of the ladder here, not that tier 1 was forgotten.",
            "",
        ]

    L += ["## Dimensions", ""]
    synonyms = [
        (c.get("name"), c.get("synonyms") or [])
        for t in tbls
        for c in (t.get("column_configs") or [])
        if c.get("synonyms")
    ]
    if synonyms:
        L += [f"- `{col}` — also called: {', '.join(syns)}" for col, syns in synonyms]
    else:
        L += [
            "- TODO: how key dimensions are encoded, and where the same concept is",
            "  named differently across tables.",
        ]
    L += [""]

    L += ["## Key Tables", ""]
    for t in tbls:
        if t.get("_metric_view"):
            continue
        L += [
            f"### `{t.get('identifier', '?')}`",
            f"- **Grain**: TODO · **Scope/exclusions**: TODO",
            f"- **Usage**: {t.get('description') or 'TODO: when to use it, when NOT to, join keys, required filters.'}",
            "",
        ]
    L += [
        "### Deprecated / near-duplicate tables",
        "TODO: the tables that look like they answer this domain and must not be used,",
        "and why. A Genie space lists what to query, never what to avoid — so this is the",
        "list the evals' `must_not_include` is built from.",
        "",
        "## Blessed Dashboards",
        "",
        "TODO: the governed dashboard that already publishes each common number here, so",
        "the agent reconciles against it instead of re-deriving it. A query that disagrees",
        "with the dashboard the stakeholder already reads is a finding, not a result.",
        "",
    ]

    L += ["## Gotchas", ""]
    L += [f"- {r}" for r in rules] or [
        "- TODO: the wrong-answer modes a senior analyst would warn about."
    ]
    L += [
        "",
        "<!-- TODO: these are Genie's free-text rules verbatim. A good gotcha names the",
        "     mechanism, not just the rule: 'net_revenue is already refund-adjusted;",
        "     subtracting fact_refunds double-counts' beats 'do not subtract refunds'. -->",
        "",
    ]

    L += ["## Best Practices / Common Query Patterns", ""]
    for s in snippets:
        if s is hygiene:
            continue
        L += [f"- **{s.get('display_name', 'TODO')}** — `{s.get('sql', '')}`"]
        if s.get("instruction"):
            L += [f"  - {s['instruction']}"]
        if s.get("synonyms"):
            L += [f"  - asked as: {', '.join(s['synonyms'])}"]
    if not any(s is not hygiene for s in snippets):
        L += ["- TODO: the default cuts and standard patterns for this domain."]
    L += [
        "",
        "<!-- TODO: a human owns every metric definition. Genie snippets are candidates,",
        "     not definitions — promote each into the semantic layer or delete it. -->",
        "",
        "## Cross-References",
        "",
        "- TODO: neighbouring domain docs that own adjacent questions, and the questions",
        "  this doc must hand off to them.",
        "",
    ]
    return "\n".join(L)


def eval_case(domain: str, idx: int, question: str, gold_sql: str) -> dict:
    refs = sorted({".".join(m) for m in TABLE_RE.findall(gold_sql)})
    case = {
        "id": f"{domain}-{idx:03d}",
        "domain": domain,
        "question": question,
        "expect_tier": "governed_table" if gold_sql else "TODO",
        "must_include": refs,
        "must_not_include": [],
        "note": "migrated from Genie"
        + (
            # Genie's own SQL is a candidate answer, not ground truth: it was written
            # against tier 2 because Genie has no tier 1, and nobody re-checked it.
            " — gold SQL unverified; must_include is only the tables it named. Add the"
            " hygiene filter and the deprecated tables, and confirm no metric covers"
            " this before accepting governed_table."
            if gold_sql
            else " sample question — no gold SQL, needs a human"
        ),
    }
    if gold_sql:
        case["gold_sql"] = " ".join(gold_sql.split())
    return case


def router_entry(domain: str, name: str, desc: str) -> str:
    return (
        f"| {name} | [`references/{domain}.md`](references/{domain}.md) | "
        f"{desc or 'TODO'} | TODO: adjacent domains that own these questions instead |"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", help="genie space YAML/JSON, or - for stdin")
    ap.add_argument("--domain", help="short slug; defaults to the space name")
    ap.add_argument(
        "--out",
        default="analytics/references",
        type=Path,
        help="reference-doc dir (default: analytics/references)",
    )
    ap.add_argument("--evals-out", default="analytics/evals", type=Path)
    ap.add_argument("--space", help="which resources.genie_spaces key, if a bundle yml")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.source:
        ap.error("source is required")

    stdin = args.source == "-"
    raw = sys.stdin.read() if stdin else Path(args.source).read_text()
    base = None if stdin else Path(args.source).parent
    doc = load(raw, base, args.space)
    name, desc = space_meta(doc)
    domain = args.domain or re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    tbls = tables(doc)
    rules, snippets = instructions(doc)
    benches = benchmarks(doc)

    ref_path = args.out / f"{domain}.md"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(reference_doc(domain, name, desc, tbls, rules, snippets))

    eval_path = args.evals_out / f"{domain}.jsonl"
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    cases = [eval_case(domain, i, q, sql) for i, (q, sql) in enumerate(benches, 1) if q]
    eval_path.write_text("".join(json.dumps(c) + "\n" for c in cases))

    todos = ref_path.read_text().count("TODO") + sum(
        c["expect_tier"] == "TODO" for c in cases
    )
    print(
        f"wrote {ref_path}  ({len(tbls)} sources, {len(rules)} rules, {len(snippets)} snippets)"
    )
    print(
        f"wrote {eval_path} ({len(cases)} cases, {sum(1 for c in cases if 'gold_sql' in c)} with gold SQL)"
    )
    print(f"\n{todos} TODOs need a human. Register the doc in {args.out}/INDEX.md:\n")
    print(router_entry(domain, name, desc))
    return 0


SAMPLE = """
config: {name: Orders, description: order questions, sample_questions: ["How many orders?"]}
data_sources:
  tables: [{identifier: an.core.fact_orders, description: one order per row}]
  metric_views: [{identifier: an.core.rev, measures: [net_revenue], dimensions: [dt]}]
instructions:
  text: "exclude test orders"
  sql_snippets: [{display_name: Hygiene filter, sql: "is_test = false"}]
benchmarks:
  - question: revenue last month?
    answer: [{format: SQL, content: ["SELECT 1 FROM an.core.fact_orders"]}]
"""


# The real thing: Databricks' documented serialized_space v2, where every scalar is
# wrapped in a list. Copied from the Genie Agents API reference. If the migrator only
# parses the shapes we invented, it doesn't migrate anything real.
V2 = json.dumps(
    {
        "version": 2,
        "config": {
            "name": "Sales",
            "description": ["Sales questions"],
            "sample_questions": [
                {
                    "id": "a1b2c3d4e5f60000000000000000000a",
                    "question": ["What were total sales last month?"],
                }
            ],
        },
        "data_sources": {
            "tables": [
                {
                    "identifier": "sales.analytics.customers",
                    "description": ["Customer master data"],
                    "column_configs": [
                        {
                            "column_name": "customer_id",
                            "description": ["Unique identifier"],
                            "synonyms": ["cust_id"],
                        }
                    ],
                }
            ]
        },
        "instructions": {
            "text_instructions": [
                {
                    "id": "01f0b37c378e1c9100000000000000a1",
                    "content": ["Always exclude test rows."],
                }
            ],
            "example_question_sqls": [
                {
                    "id": "01f0821116d912db00000000000000b1",
                    "question": ["Show top customers"],
                    "sql": ["SELECT * FROM sales.analytics.customers"],
                }
            ],
        },
    }
)


def selftest_v2() -> None:
    doc = load(V2)
    name, desc = space_meta(doc)
    assert (name, desc) == ("Sales", "Sales questions"), (name, desc)

    tbls = tables(doc)
    assert tbls[0]["identifier"] == "sales.analytics.customers"
    assert tbls[0]["description"] == "Customer master data", tbls[0]["description"]
    col = tbls[0]["column_configs"][0]
    assert col["name"] == "customer_id" and col["synonyms"] == ["cust_id"], col

    rules, _ = instructions(doc)
    assert rules == ["Always exclude test rows."], rules

    benches = benchmarks(doc)
    assert benches[0] == (
        "Show top customers",
        "SELECT * FROM sales.analytics.customers",
    ), benches[0]
    assert benches[1] == ("What were total sales last month?", ""), benches[1]

    # and the whole pipeline produces a usable doc + eval, not stringified lists
    md = reference_doc("sales", name, desc, tbls, rules, [])
    assert "['" not in md and "Customer master data" in md, "list leaked into the doc"
    # a space with no metric view still gets the tier-1 section, or the doc quietly
    # teaches the agent that governed tables are the top of the ladder
    assert "## Metrics (tier 1" in md and "no metric view" in md
    assert "Use For / Do NOT Use For" in md, "no routing trigger in the doc"
    case = eval_case("sales", 1, *benches[0])
    assert case["must_include"] == ["sales.analytics.customers"], case


# The exact envelope `databricks api get .../genie/spaces/$ID?include_serialized_space=true`
# returns: title/description are siblings of serialized_space, not inside it; benchmarks
# wraps its list under "questions"; free-text rules are markdown bullets; gold SQL is
# backtick-quoted. selftest_v2 above missed all four because its fixture skips the outer
# envelope and never uses backticks or bullets.
LIVE_API = json.dumps(
    {
        "title": "Bakehouse Sales Starter Space",
        "description": "fictional bakery sales and inventory data",
        "warehouse_id": "w1",
        "serialized_space": json.dumps(
            {
                "version": 2,
                "config": {},
                "data_sources": {
                    "tables": [{"identifier": "samples.bakehouse.sales_transactions"}]
                },
                "instructions": {
                    "text_instructions": [
                        {
                            "content": [
                                "* Always include franchise name with franchise ID\n",
                                "* Fiscal year starts in February\n",
                            ]
                        }
                    ]
                },
                "benchmarks": {
                    "questions": [
                        {
                            "question": ["Top product?"],
                            "answer": [
                                {
                                    "format": "SQL",
                                    "content": [
                                        "SELECT `product` FROM "
                                        "`samples`.`bakehouse`.`sales_transactions`"
                                    ],
                                }
                            ],
                        }
                    ]
                },
            }
        ),
    }
)


def selftest_live_api() -> None:
    doc = load(LIVE_API)
    name, desc = space_meta(doc)
    assert name == "Bakehouse Sales Starter Space", name
    assert desc == "fictional bakery sales and inventory data", desc

    rules, _ = instructions(doc)
    assert rules == [
        "Always include franchise name with franchise ID",
        "Fiscal year starts in February",
    ], rules

    benches = benchmarks(doc)
    assert benches[0][0] == "Top product?", benches
    assert "sales_transactions" in benches[0][1], benches

    case = eval_case("bakehouse", 1, *benches[0])
    assert case["must_include"] == ["samples.bakehouse.sales_transactions"], case


def selftest() -> int:
    selftest_v2()
    selftest_live_api()
    doc = load(SAMPLE)
    name, desc = space_meta(doc)
    assert (name, desc) == ("Orders", "order questions"), (name, desc)
    tbls = tables(doc)
    assert [t["identifier"] for t in tbls] == ["an.core.fact_orders", "an.core.rev"]
    rules, snippets = instructions(doc)
    assert rules == ["exclude test orders"] and snippets[0]["sql"] == "is_test = false"
    # hand-wrapped rules stay one bullet; sentence-ended lines split
    assert split_rules("no test\nrows allowed.\nUse UTC.") == [
        "no test rows allowed.",
        "Use UTC.",
    ]
    benches = benchmarks(doc)
    assert benches[0][0] == "revenue last month?" and "SELECT 1" in benches[0][1]
    assert benches[1] == ("How many orders?", ""), benches
    cases = [eval_case("orders", i, q, s) for i, (q, s) in enumerate(benches, 1)]
    assert cases[0]["must_include"] == ["an.core.fact_orders"], cases[0]
    assert cases[1]["expect_tier"] == "TODO" and "gold_sql" not in cases[1]

    doc_md = reference_doc("orders", name, desc, tbls, rules, snippets)
    assert "WHERE is_test = false" in doc_md and "an.core.fact_orders" in doc_md
    assert "TODO" in doc_md  # grain is never inferable from a Genie space

    # alternate export shapes must survive
    assert space_meta(load('{"display_name": "X"}'))[0] == "X"
    assert tables(load('{"table_identifiers": ["a.b.c"]}'))[0]["identifier"] == "a.b.c"
    assert instructions(load('{"instructions": ["no test rows"]}'))[0] == [
        "no test rows"
    ]
    assert instructions(load('{"instructions": [{"title": "T", "content": "C"}]}'))[
        0
    ] == ["T: C"]
    assert (
        space_meta(
            load('{"serialized_space": "{\\"config\\": {\\"name\\": \\"Y\\"}}"}')
        )[0]
        == "Y"
    )
    # bundle databricks.yml: inline resource, sidecar file_path, and space selection
    inline = load("""
resources:
  genie_spaces:
    orders_space:
      title: Orders From Bundle
      warehouse_id: w1
      data_sources: {tables: [{identifier: a.b.c}]}
""")
    assert space_meta(inline)[0] == "Orders From Bundle", space_meta(inline)
    assert tables(inline)[0]["identifier"] == "a.b.c"

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        side = Path(tmp) / "orders.geniespace.json"
        side.write_text(
            json.dumps({"data_sources": {"tables": [{"identifier": "x.y.z"}]}})
        )
        bundle = (
            "resources:\n  genie_spaces:\n    a:\n      title: From Sidecar\n"
            f"      file_path: {side.name}\n    b:\n      title: Other\n"
        )
        doc = load(bundle, Path(tmp))
        assert space_meta(doc)[0] == "From Sidecar", space_meta(doc)
        assert tables(doc)[0]["identifier"] == "x.y.z"
        assert space_meta(load(bundle, Path(tmp), space="b"))[0] == "Other"

    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
