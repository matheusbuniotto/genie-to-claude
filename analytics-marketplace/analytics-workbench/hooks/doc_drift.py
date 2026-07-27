#!/usr/bin/env python3
"""Flag a data-model change whose reference doc wasn't touched in the same change.

Wired as a PostToolUse hook. Stateless on purpose: if the edited model is named in a
reference doc, say so and move on. Advisory only — it never blocks an edit.

The rule it enforces is the one that keeps docs from rotting: the PR that changes a
model is the PR that updates the doc describing it.

    python3 doc_drift.py --selftest
"""

import json
import re
import sys
from pathlib import Path

MODEL_PATH = re.compile(r"(models|transformations|dbt|marts|warehouse)/.*\.(sql|py)$")
REFS = Path("analytics/references")


def model_stem(file_path: str) -> str | None:
    """The model name if this looks like a warehouse model, else None."""
    if not file_path or not MODEL_PATH.search(file_path):
        return None
    return Path(file_path).stem


def docs_mentioning(stem: str, refs: Path) -> list[str]:
    """A domain doc is either a flat file or a folder (SKILL.md + a flat reference.md
    sibling) — check both shapes, reported as a path relative to the references dir."""
    if not stem or not refs.is_dir():
        return []
    paths = list(refs.glob("*.md")) + list(refs.glob("*/*.md"))
    return sorted(
        str(p.relative_to(refs))
        for p in paths
        if p.name != "INDEX.md" and stem in p.read_text(errors="ignore")
    )


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    stem = model_stem((event.get("tool_input") or {}).get("file_path", ""))
    docs = docs_mentioning(stem, REFS)
    if not docs:
        return 0  # not a model, or nothing documents it yet

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"`{stem}` is described in {', '.join(docs)}. If this change altered its "
                        "grain, filters, columns, or semantics, update the doc in this same change "
                        "— a reference doc that lags its model produces confident wrong answers. "
                        "Add an eval case if the change fixes a wrong-answer mode."
                    ),
                }
            }
        )
    )
    return 0


def selftest() -> int:
    assert model_stem("dbt/models/core/fact_orders.sql") == "fact_orders"
    assert model_stem("transformations/marts/rev.py") == "rev"
    assert model_stem("analytics/references/orders.md") is None
    assert model_stem("src/app/models/user.rb") is None  # not sql/py
    assert model_stem("") is None

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        refs = Path(tmp)
        (refs / "orders.md").write_text("### `analytics.core.fact_orders`")
        (refs / "INDEX.md").write_text("fact_orders")  # index never counts
        assert docs_mentioning("fact_orders", refs) == ["orders.md"]
        assert docs_mentioning("fact_widgets", refs) == []
        assert docs_mentioning("fact_orders", refs / "nope") == []

        # folder-shaped domain doc: the mention can live in SKILL.md or reference.md
        (refs / "marketing").mkdir(parents=True)
        (refs / "marketing" / "SKILL.md").write_text("no mention here")
        (refs / "marketing" / "reference.md").write_text(
            "### `analytics.core.fact_campaigns`"
        )
        assert docs_mentioning("fact_campaigns", refs) == ["marketing/reference.md"]
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
