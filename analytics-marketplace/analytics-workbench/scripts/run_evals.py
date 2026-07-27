#!/usr/bin/env python3
"""Run the offline eval set against the analytics agent and append results as telemetry.

    python3 run_evals.py                      # all of analytics/evals/*.jsonl
    python3 run_evals.py --filter orders-00   # one slice, for an ablation
    python3 run_evals.py --selftest           # check the grader, call no model
    python3 run_evals.py --agent-cmd ./my-bot # eval a different agent on the same set
    python3 run_evals.py --gold-cmd 'bq query --format=csv'   # number parity

Run from the repo root. Grades the agent's *query and reasoning text*, not its number,
so evals don't go stale when the underlying data moves. Results append to
analytics/evals/results.jsonl — one row per question per run, meant to be loaded into a
warehouse table and queried over time, not read once as a test log.

`--gold-cmd` turns on **number parity**, which is the question a migration actually has
to answer: does Claude return what the old system returned? For every case carrying
`gold_sql`, that SQL is executed to get the source-of-truth number and the agent's answer
must contain it. Use it on a migrated slice, where the gold SQL came out of the tool you
are replacing — it is the difference between "the agent cited the right table" and "the
agent got the right answer".
"""

import argparse
import glob
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EVALS_DIR = Path("analytics/evals")  # project-owned, relative to the repo root
RESULTS = EVALS_DIR / "results.jsonl"

# Anchored on the provenance footer ("**Source:** governed table") so that merely
# *mentioning* a tier — "the semantic layer doesn't cover this" — never counts as using it.
TIER_LABELS = {
    "semantic_layer": "semantic layer",
    "governed_table": "governed table",
    "raw": "raw exploration",
    "escalate": None,  # no footer expected; graded by must_include only
}
FOOTER = r"source:\s*\**\s*{}"

NUMBER = re.compile(r"-?\d[\d,_]*(?:\.\d+)?")
TOLERANCE = 0.005  # 0.5% — absorbs rounding and display formatting, not a wrong join


def numbers(text: str) -> list[float]:
    out = []
    for token in NUMBER.findall(text):
        try:
            out.append(float(token.replace(",", "").replace("_", "")))
        except ValueError:
            pass
    return out


def run_sql(sql: str, cmd: str, keep_qualified: bool = False) -> list[float]:
    """Execute gold SQL and return the numbers it printed.

    Three-part names are stripped to bare table names by default: gold SQL exported from
    a warehouse tool carries `catalog.schema.table`, while the fixture that lets evals run
    offline holds the same tables unqualified. Pass --keep-qualified when the gold command
    really does point at the qualified warehouse.
    """
    if not keep_qualified:
        sql = re.sub(r"\b\w+\.\w+\.(\w+)", r"\1", sql)
        # ponytail: `DATE '2026-01-01'` only, not a dialect translator. Gold SQL that uses
        # more of the source warehouse's dialect wants --gold-cmd pointed at that
        # warehouse, or a rewritten gold query — not a transpiler living in this file.
        sql = re.sub(r"\bDATE\s+('\d{4}-\d{2}-\d{2}')", r"\1", sql, flags=re.I)
    proc = subprocess.run(
        cmd, shell=True, input=sql, capture_output=True, text=True, timeout=120
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[:300] or "gold SQL failed")
    return numbers(proc.stdout)


def number_ok(gold: list[float], response: str, tol: float = TOLERANCE) -> bool:
    """Does the answer state the source-of-truth number anywhere?

    Every value the gold query returned must appear. A rate is matched at either scale —
    gold `0.0512` against an answer reading "5.1%" is the same finding, not a miss.
    """
    said = numbers(response)
    return all(
        any(
            abs(v - g) <= tol * max(abs(g), 1e-9)
            or abs(v - g * 100) <= tol * max(abs(g * 100), 1e-9)
            for v in said
        )
        for g in gold
    )


def grade(eval_case: dict, response: str, gold: list[float] | None = None) -> dict:
    """Assertion-based grading. Case-insensitive substring match, one flag per rule."""
    text = response.lower()
    missing = [s for s in eval_case.get("must_include", []) if s.lower() not in text]
    present = [s for s in eval_case.get("must_not_include", []) if s.lower() in text]

    label = TIER_LABELS.get(eval_case.get("expect_tier"))
    tier_ok = bool(re.search(FOOTER.format(label), text)) if label else True
    # None = parity not checked (no gold SQL, or --gold-cmd not given), which is not a pass
    numbers_ok = None if gold is None else number_ok(gold, response)

    return {
        "passed": not missing and not present and tier_ok and numbers_ok is not False,
        "missing": missing,
        "forbidden_present": present,
        "tier_ok": tier_ok,
        "numbers_ok": numbers_ok,
        "gold_values": gold,
    }


def ask(question: str, model: str | None, agent_cmd: str | None) -> tuple[str, dict]:
    """One agent turn, in the repo root so the project's reference docs are in scope.

    `agent_cmd` swaps the agent out: any shell command that reads the question on stdin
    and prints the answer on stdout. Used to exercise the harness without burning tokens,
    and to eval a non-Claude-Code surface (a Slack bot, an API service) on the same set.
    """
    if agent_cmd:
        proc = subprocess.run(
            agent_cmd,
            shell=True,
            input=question,
            capture_output=True,
            text=True,
            timeout=600,
        )
        return (
            proc.stdout
            if proc.returncode == 0
            else f"<error> {proc.stderr.strip()[:500]}"
        ), {}

    cmd = ["claude", "-p", question, "--output-format", "json"]
    if model:
        cmd += ["--model", model]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        return f"<error> {proc.stderr.strip()[:500]}", {}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.stdout, {}
    return payload.get("result", ""), payload


def docs_version() -> str:
    """git SHA of analytics/, so a result row points at the docs that produced it."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", "analytics"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() or "untracked"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", default=[str(EVALS_DIR / "*.jsonl")])
    ap.add_argument(
        "--model", help="pin a model; omit to use the claude CLI's own default"
    )
    ap.add_argument("--filter", help="only run eval ids matching this regex")
    ap.add_argument(
        "--agent-cmd",
        help="shell command answering a question on stdin (default: the claude CLI)",
    )
    ap.add_argument(
        "--results", type=Path, default=RESULTS, help=f"telemetry file ({RESULTS})"
    )
    ap.add_argument(
        "--gold-cmd",
        help="shell command running SQL from stdin; enables number parity on gold_sql",
    )
    ap.add_argument(
        "--keep-qualified",
        action="store_true",
        help="don't strip catalog.schema from gold SQL before running it",
    )
    ap.add_argument(
        "--selftest", action="store_true", help="check the grader, run nothing"
    )
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    sha = docs_version()
    cases = []
    for pattern in args.files:
        for path in sorted(glob.glob(pattern)):
            if Path(path).name == args.results.name:
                continue
            with open(path) as fh:
                cases += [json.loads(line) for line in fh if line.strip()]
    if args.filter:
        cases = [c for c in cases if re.search(args.filter, c["id"])]
    if not cases:
        print("no eval cases matched", file=sys.stderr)
        return 1

    who = args.agent_cmd or f"claude CLI ({args.model or 'default model'})"
    print(
        f"running {len(cases)} case(s) against {who} — real calls, not a dry run",
        file=sys.stderr,
    )

    passed = 0
    checked = 0
    args.results.parent.mkdir(parents=True, exist_ok=True)
    with open(args.results, "a") as out:
        for case in cases:
            gold, gold_error = None, None
            if args.gold_cmd and case.get("gold_sql"):
                try:
                    gold = run_sql(case["gold_sql"], args.gold_cmd, args.keep_qualified)
                except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                    gold, gold_error = [], str(exc)

            started = time.monotonic()
            response, meta = ask(case["question"], args.model, args.agent_cmd)
            result = grade(case, response, gold)
            if gold_error:
                # a gold query that no longer runs is a finding about the eval set, and
                # the loudest place to surface it is a failing case
                result.update(passed=False, gold_error=gold_error)
            checked += result["numbers_ok"] is not None
            passed += result["passed"]
            out.write(
                json.dumps(
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "eval_id": case["id"],
                        "domain": case.get("domain"),
                        "docs_sha": sha,
                        "model": args.agent_cmd or args.model,
                        "duration_s": round(time.monotonic() - started, 1),
                        "tokens": (meta.get("usage") or {}).get("output_tokens"),
                        "cost_usd": meta.get("total_cost_usd"),
                        "response": response,
                        **result,
                    }
                )
                + "\n"
            )
            mark = "PASS" if result["passed"] else "FAIL"
            detail = (
                ""
                if result["passed"]
                else f"  missing={result['missing']} forbidden={result['forbidden_present']}"
                f" tier_ok={result['tier_ok']} numbers_ok={result['numbers_ok']}"
                + (f" gold_error={gold_error}" if gold_error else "")
            )
            print(f"{mark} {case['id']}{detail}")

    rate = passed / len(cases)
    parity = (
        f" · number parity checked on {checked}/{len(cases)}" if args.gold_cmd else ""
    )
    print(
        f"\n{passed}/{len(cases)} passed ({rate:.0%}) · sha={sha[:8]}{parity}"
        f" · → {args.results}"
    )
    # ponytail: a flat 90% gate, per-domain gating when domains actually diverge
    return 0 if rate >= 0.9 else 1


def selftest() -> int:
    case = {
        "must_include": ["fact_orders", "is_test"],
        "must_not_include": ["orders_v1"],
        "expect_tier": "governed_table",
    }
    good = "SELECT ... FROM fact_orders WHERE is_test = false\n> Source: governed table"
    assert grade(case, good)["passed"]
    assert not grade(case, good.replace("is_test = false", ""))["passed"]
    assert not grade(case, good + " union orders_v1")["passed"]
    assert not grade(case, good.replace("governed table", "raw exploration"))["passed"]
    # the tier must come from the footer, not from prose mentioning it
    talked_about_it = good.replace(
        "> Source: governed table",
        "I checked the governed table docs first.\n> Source: raw exploration",
    )
    assert not grade(case, talked_about_it)["tier_ok"], "tier must be footer-anchored"
    assert grade(
        {"expect_tier": "escalate", "must_include": ["run it yourself"]},
        "here is the SQL, run it yourself",
    )["passed"]

    # number parity: the answer must state what the gold query returned
    assert number_ok([1234567.0], "net revenue was R$ 1,234,567")
    assert number_ok([1234567.0], "R$ 1,234,566 after rounding")  # inside tolerance
    assert not number_ok([1234567.0], "net revenue was R$ 1,199,000")
    assert number_ok([0.0512], "refund rate was 5.12%"), "rate scale must match"
    assert number_ok([12.0, 34.0], "12 orders and 34 items")
    assert not number_ok([12.0, 34.0], "12 orders"), "every gold value must appear"
    # unchecked parity is not a pass, but it isn't a failure either
    assert grade(case, good)["numbers_ok"] is None
    assert not grade(case, good, gold=[99.0])["passed"]
    assert grade(case, good + " total 99", gold=[99.0])["passed"]
    # three-part names are stripped so gold SQL runs against the offline fixture
    assert run_sql.__doc__ and re.sub(r"\b\w+\.\w+\.(\w+)", r"\1", "FROM a.b.c") == (
        "FROM c"
    )
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
