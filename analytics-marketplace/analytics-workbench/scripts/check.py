#!/usr/bin/env python3
"""Repo-level invariants for an analytics-agent project. No model calls, no credentials.

    python3 check.py            # from the repo root
    python3 check.py --selftest

This is the cheap gate that runs on every PR. It cannot tell you whether the agent gives
correct answers — only `run_evals.py` does that. What it catches is the failure mode that
precedes wrong answers: reference docs and eval sets drifting out of shape.

Checks:
  1. every eval case is well-formed, ids unique, tiers valid
  2. every eval asserts on something — a case with no assertions always "passes"
  3. every domain doc is registered in the router INDEX
  4. every relative markdown link resolves
  5. every reference doc carries the sections the skeleton requires
"""

import argparse
import json
import re
import sys
from pathlib import Path

REFS = Path("analytics/references")
EVALS = Path("analytics/evals")
TIERS = {"semantic_layer", "governed_table", "raw", "escalate"}
REQUIRED_SECTIONS = ("Entity Grain", "Key Tables", "Gotchas", "Cross-References")
# a doc that documents metrics rather than tables declares itself with this marker
OPT_OUT = "<!-- not-a-domain-doc -->"


def check_evals(evals: Path) -> list[str]:
    bad, ids = [], set()
    for path in sorted(evals.glob("*.jsonl")):
        if path.name == "results.jsonl":
            continue
        for n, line in enumerate(path.open(), 1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                bad.append(f"{path}:{n} invalid JSON: {exc}")
                continue
            where = f"{path.name}:{case.get('id', f'line {n}')}"
            for field in ("id", "question", "expect_tier"):
                if not case.get(field):
                    bad.append(f"{where} missing '{field}'")
            if case.get("expect_tier") == "TODO":
                # migrate_genie.py emits this deliberately; the red build is the gate
                bad.append(f"{where} unfinished migration — set expect_tier and assert")
            elif case.get("expect_tier") not in TIERS:
                bad.append(f"{where} bad tier {case.get('expect_tier')!r}")
            if case.get("id") in ids:
                bad.append(f"{where} duplicate id")
            ids.add(case.get("id"))
            # an eval with nothing to assert is a case that can never fail
            if not case.get("must_include") and not case.get("must_not_include"):
                bad.append(f"{where} has no assertions — it can never fail")
    if not ids:
        bad.append(f"no eval cases found in {evals}/")
    return bad


def check_router(refs: Path) -> list[str]:
    index = refs / "INDEX.md"
    if not index.is_file():
        return [f"{index} missing — the router is what makes docs findable"]
    text = index.read_text()
    return [
        f"{doc.name} is not registered in INDEX.md — the agent will never find it"
        for doc in sorted(refs.glob("*.md"))
        if doc.name != "INDEX.md" and doc.name not in text
    ]


def check_sections(refs: Path) -> list[str]:
    """Domain docs must carry the skeleton. Catalogs and indexes opt out explicitly."""
    bad = []
    for doc in sorted(refs.glob("*.md")):
        text = doc.read_text()
        if doc.name == "INDEX.md" or OPT_OUT in text:
            continue
        missing = [s for s in REQUIRED_SECTIONS if s not in text]
        if missing:
            bad.append(f"{doc.name} missing section(s): {', '.join(missing)}")
    return bad


def check_links(root: Path) -> list[str]:
    bad = []
    for md in sorted(root.rglob("*.md")):
        if ".claude" in md.parts or "node_modules" in md.parts:
            continue
        for link in re.findall(r"\]\((?!https?:|#|mailto:)([^)]+)\)", md.read_text()):
            target = (md.parent / link.split("#")[0]).resolve()
            if not target.exists():
                bad.append(f"{md}: dangling link -> {link}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", type=Path, default=REFS)
    ap.add_argument("--evals", type=Path, default=EVALS)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    problems = (
        check_evals(args.evals)
        + check_router(args.refs)
        + check_sections(args.refs)
        + check_links(args.root)
    )
    for p in problems:
        print(f"FAIL {p}")
    print(f"\n{len(problems)} problem(s)" if problems else "\nall checks passed")
    return 1 if problems else 0


def selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        refs, evals = root / "references", root / "evals"
        refs.mkdir(), evals.mkdir()

        # a healthy project passes
        (refs / "INDEX.md").write_text("[orders](orders.md)")
        (refs / "orders.md").write_text(
            "## Entity Grain\n## Key Tables\n## Gotchas\n## Cross-References"
        )
        (evals / "orders.jsonl").write_text(
            json.dumps(
                {
                    "id": "o-1",
                    "question": "q",
                    "expect_tier": "raw",
                    "must_include": ["fact_orders"],
                }
            )
            + "\n"
        )
        assert check_evals(evals) == [], check_evals(evals)
        assert check_router(refs) == [] and check_sections(refs) == []

        # an unregistered doc is invisible to the agent
        (refs / "orphan.md").write_text(
            "## Entity Grain\n## Key Tables\n## Gotchas\n## Cross-References"
        )
        assert len(check_router(refs)) == 1

        # a doc missing skeleton sections is flagged
        (refs / "thin.md").write_text("## Key Tables")
        assert any("thin.md" in p for p in check_sections(refs))

        # ...unless it declares itself not a domain doc
        (refs / "thin.md").write_text("## Key Tables\n" + OPT_OUT)
        assert not any("thin.md" in p for p in check_sections(refs))

        # assertion-free and malformed cases are caught
        (evals / "bad.jsonl").write_text(
            json.dumps({"id": "b-1", "question": "q", "expect_tier": "raw"})
            + "\n"
            + json.dumps(
                {
                    "id": "b-1",
                    "question": "q",
                    "expect_tier": "nope",
                    "must_include": ["x"],
                }
            )
            + "\n"
        )
        found = " ".join(check_evals(evals))
        assert "no assertions" in found and "bad tier" in found and "duplicate" in found

        # a freshly migrated Genie case fails as an unfinished migration, not a typo
        (evals / "bad.jsonl").write_text(
            json.dumps({"id": "m-1", "question": "q", "expect_tier": "TODO"}) + "\n"
        )
        assert "unfinished migration" in " ".join(check_evals(evals))

        # dangling links are caught
        (root / "a.md").write_text("[gone](nope.md)")
        assert len(check_links(root)) == 1
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
