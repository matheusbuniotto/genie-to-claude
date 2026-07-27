#!/usr/bin/env python3
"""Package analytics/references/ domain Skills for claude.ai / Claude Desktop upload.

    python3 package_skills.py                  # every domain + a router Skill
    python3 package_skills.py --domain orders   # one domain only, no router
    python3 package_skills.py --selftest        # check the packaging, write nothing

Neither claude.ai nor Claude Desktop runs Claude Code plugins — no subagents, hooks, or
Bash tool — but both accept an uploaded Skill (a zip with the skill folder as its root,
e.g. `orders/SKILL.md`) under Settings > Capabilities, shared across the account. Every
analytics/references/<domain>/ folder is already shaped that way; this just zips it.

Two things a raw copy would get wrong:

1. **The frontmatter `name` field.** claude.ai validates it: lowercase letters, numbers
   and hyphens only, max 64 chars. A hand-authored or migrated SKILL.md often carries
   the human title instead ("Orders & Revenue") because Claude Code never enforces
   this — nothing there auto-loads analytics/references/ as a real Skill, so it's
   never spec-checked until now. Rewritten to the domain slug at packaging time.
2. **No router.** Inside Claude Code, `warehouse-knowledge` reads INDEX.md before
   opening any domain doc, so N domains never compete for attention. Uploaded
   standalone, N domain Skills compete on their own descriptions with nothing funnelling
   them. This script also builds a `warehouse-router` Skill from INDEX.md's domain map
   to do that same job on claude.ai / Desktop.
"""

import argparse
import re
import sys
import zipfile
from pathlib import Path

REFS = Path("analytics/references")
OUT = Path("dist/skills")
ROUTER_NAME = "warehouse-router"

ROW_RE = re.compile(
    r"^\|\s*(.+?)\s*\|\s*\[`?([\w-]+)/SKILL\.md`?\]\([^)]+\)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$",
    re.M,
)


def domain_folders(refs: Path) -> list[Path]:
    return sorted(p.parent for p in refs.glob("*/SKILL.md"))


def slugify_skill_name(s: str) -> str:
    """claude.ai's Skill `name`: lowercase letters, numbers, hyphens only, <=64 chars."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:64] or "skill"


def patch_skill_name(skill_md: str, domain: str) -> str:
    return re.sub(
        r"(?m)^name:.*$", f"name: {slugify_skill_name(domain)}", skill_md, count=1
    )


def package_domain(folder: Path, out_dir: Path) -> Path:
    patched = patch_skill_name((folder / "SKILL.md").read_text(), folder.name)
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{folder.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{folder.name}/SKILL.md", patched)
        for f in sorted(folder.rglob("*")):
            if f.is_file() and f.name != "SKILL.md":
                zf.write(f, arcname=f"{folder.name}/{f.relative_to(folder)}")
    return zip_path


PATH_MENTION_RE = re.compile(r"`?([\w-]+)/SKILL\.md`?")


def _delink(text: str) -> str:
    """A cross-reference like '(→ marketing/SKILL.md)' names a file that won't exist
    once the domain is uploaded as its own standalone Skill — rewrite it to the
    (slugified) Skill name instead."""
    return PATH_MENTION_RE.sub(lambda m: f"`{slugify_skill_name(m.group(1))}`", text)


def router_rows(index_text: str) -> list[tuple[str, str, str, str]]:
    """Domain map rows that point at a Skill folder — flat catalogs (metrics.md-style)
    have no `/SKILL.md` in their Doc cell and are deliberately left out here."""
    return [
        (domain, slugify_skill_name(slug), _delink(use_for), _delink(not_for))
        for domain, slug, use_for, not_for in ROW_RE.findall(index_text)
    ]


def router_skill_md(rows: list[tuple[str, str, str, str]]) -> str:
    lines = [
        "# Warehouse Router",
        "",
        "Check this Skill FIRST for any question that needs numbers from the data",
        "warehouse. It says which domain Skill to open — do not query before that.",
        "",
        "## Domain map",
        "",
        "| Domain | Skill | Use for | Do NOT use for |",
        "|---|---|---|---|",
    ]
    lines += [f"| {d} | `{s}` | {u} | {n} |" for d, s, u, n in rows]
    lines += [
        "",
        "Open the matching domain Skill by name before writing any query. If no row",
        "matches, say the domain isn't documented yet rather than guessing a table.",
    ]
    front = (
        "---\n"
        f"name: {ROUTER_NAME}\n"
        'description: "IF the question needs numbers from the data warehouse -> check '
        "this Skill first to find which domain Skill owns it. DO NOT use for anything "
        'else, and do not query before opening the domain Skill this points to."\n'
        "---\n"
    )
    return front + "\n" + "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", type=Path, default=REFS)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--domain", help="package one domain only, skip the router")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    folders = domain_folders(args.refs)
    if args.domain:
        folders = [f for f in folders if f.name == args.domain]
        if not folders:
            print(
                f"no domain folder named {args.domain!r} under {args.refs}",
                file=sys.stderr,
            )
            return 1

    written = [package_domain(f, args.out) for f in folders]

    index = args.refs / "INDEX.md"
    if not args.domain and index.is_file():
        rows = router_rows(index.read_text())
        if rows:
            args.out.mkdir(parents=True, exist_ok=True)
            router_path = args.out / f"{ROUTER_NAME}.zip"
            with zipfile.ZipFile(router_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"{ROUTER_NAME}/SKILL.md", router_skill_md(rows))
            written.append(router_path)

    for p in written:
        print(f"wrote {p}")

    if not args.domain:
        catalogs = sorted(
            p.name for p in args.refs.glob("*.md") if p.name != "INDEX.md"
        )
        if catalogs:
            print(
                f"\nnot packaged (flat catalog, not a Skill folder): {', '.join(catalogs)}. "
                "Paste into the router Skill's body or upload separately if the "
                "business team needs it."
            )

    print(
        f"\n{len(written)} skill zip(s) in {args.out} — upload each under "
        "Settings > Capabilities > Skills in claude.ai or Claude Desktop (shared "
        "across both, same account)."
    )
    return 0


def selftest() -> int:
    assert slugify_skill_name("Orders & Revenue") == "orders-revenue"
    assert slugify_skill_name("orders_genie") == "orders-genie"
    assert len(slugify_skill_name("x" * 100)) == 64

    patched = patch_skill_name(
        "---\nname: Orders & Revenue\ndescription: d\n---\nbody", "orders_genie"
    )
    assert "name: orders-genie" in patched and "description: d" in patched, patched

    index = (
        "| Domain | Doc | Use for | Do NOT use for |\n"
        "|---|---|---|---|\n"
        "| Orders & Revenue | [`orders_genie/SKILL.md`](orders_genie/SKILL.md) | "
        "GMV, revenue | attributed revenue |\n"
        "| Metrics catalog | [`metrics.md`](metrics.md) | KPIs | mechanics |\n"
    )
    rows = router_rows(index)
    assert rows == [
        ("Orders & Revenue", "orders-genie", "GMV, revenue", "attributed revenue")
    ], rows  # the flat metrics.md row has no /SKILL.md and is correctly dropped

    router_md = router_skill_md(rows)
    assert router_md.startswith("---\nname: warehouse-router\n"), router_md
    assert "orders-genie" in router_md and "GMV, revenue" in router_md

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "orders_genie"
        folder.mkdir()
        (folder / "SKILL.md").write_text(
            "---\nname: Orders & Revenue\ndescription: d\n---\nbody"
        )
        (folder / "reference.md").write_text("## Key Tables")
        out = Path(tmp) / "dist"
        zip_path = package_domain(folder, out)
        with zipfile.ZipFile(zip_path) as zf:
            names = sorted(zf.namelist())
            assert names == [
                "orders_genie/SKILL.md",
                "orders_genie/reference.md",
            ], names
            skill_text = zf.read("orders_genie/SKILL.md").decode()
            assert "name: orders-genie" in skill_text, skill_text

        (Path(tmp) / "INDEX.md").write_text(index)
        (Path(tmp) / "metrics.md").write_text("catalog")
        router_zip = out / f"{ROUTER_NAME}.zip"
        with zipfile.ZipFile(router_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{ROUTER_NAME}/SKILL.md", router_skill_md(rows))
        with zipfile.ZipFile(router_zip) as zf:
            assert zf.namelist() == [f"{ROUTER_NAME}/SKILL.md"]

    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
