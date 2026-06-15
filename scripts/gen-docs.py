#!/usr/bin/env python3
"""Continuous documentation generator.

Detects the project stack and (re)generates the docs that can be produced
deterministically. Source-specific API docs (TypeDoc/pdoc/Javadoc/go doc) are
delegated to the per-stack tool in CI; this script owns stack detection, the
maintenance banner, and the architecture doc — including the notes-only fallback
when no source stack is present (the seed `Rajiv.txt` case).

Usage:
    gen-docs.py --root . --out docs [--check]

--check exits non-zero if generation would change anything (used by the nightly
sweep to decide whether to open a PR), and writes nothing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BANNER = ("<!-- maintained by the docs agent — edits here may be overwritten; "
          "edit source instead -->")


def detect_stack(root: Path):
    """Return the set of detected stacks for `root`."""
    found = set()
    def has(glob):
        return any(p for p in root.rglob(glob) if ".git" not in p.parts)
    if has("package.json"):
        found.add("node")
    if has("requirements.txt") or has("pyproject.toml") or has("setup.py"):
        found.add("python")
    if has("pom.xml") or has("build.gradle"):
        found.add("java")
    if has("go.mod"):
        found.add("go")
    if has("Cargo.toml"):
        found.add("rust")
    if has("Dockerfile") or has("docker-compose.yml"):
        found.add("docker")
    return found


def architecture_doc(root: Path, stacks) -> str:
    """Build docs/architecture.md. Falls back to notes when no source stack."""
    lines = [BANNER, "# Architecture", ""]
    if stacks - {"docker"}:
        lines += [
            f"**Detected stack:** {', '.join(sorted(stacks))}",
            "",
            "## Modules",
            "",
            "_Module map is generated per-stack in CI (TypeDoc / pdoc / Javadoc / go doc)._",
            "",
        ]
    else:
        # Notes-only repo (e.g. the seed Rajiv.txt). Summarize the notes.
        notes = root / "Rajiv.txt"
        lines += ["**No source stack detected** — architecture derived from project notes.", ""]
        if notes.exists():
            lines += ["## Project Notes", "", "```", notes.read_text().strip(), "```", ""]
        else:
            lines += ["_No source and no notes file found._", ""]
    return "\n".join(lines)


# The standard doc set. Each entry: filename -> default body builder.
def _doc_set(root: Path, stacks):
    quickstart = "See `docs/operations.md` for how to run and `docs/contributing.md` to contribute."
    return {
        "README.md": "\n".join([
            BANNER, "# Project", "",
            "Documentation maintained automatically alongside code changes.", "",
            "- [Architecture](architecture.md)",
            "- [API](api.md)",
            "- [Operations](operations.md)",
            "- [Contributing](contributing.md)",
            "- [Changelog](CHANGELOG.md)", "",
            quickstart, "",
        ]),
        "architecture.md": architecture_doc(root, stacks),
        "api.md": "\n".join([
            BANNER, "# API", "",
            ("_Generated per-stack in CI._" if stacks - {"docker"}
             else "_No source stack detected — no API surface to document._"), "",
        ]),
        "operations.md": "\n".join([
            BANNER, "# Operations", "",
            "## Run", "", "_Document run/deploy steps and environment variables here._", "",
            ("## Container\n\nThis project ships a Dockerfile; document image, ports, and env."
             if "docker" in stacks else ""), "",
        ]),
        "contributing.md": "\n".join([
            BANNER, "# Contributing", "",
            "## Branch & PR rules", "",
            "- Never push to `main`/`master`; always branch.",
            "- Branches: `bot/docs-update`, `bot/devsecops-pipeline`, "
            "`bot/code-fix-YYYYMMDD`, `bot/pr-review-setup`.",
            "- Every change lands via a pull request.", "",
            "## Bot pipeline", "",
            "Scan → triage → safe-auto-fix → optimize-suggest → continuous-docs → "
            "one consolidated PR comment.", "",
        ]),
        "CHANGELOG.md": "\n".join([
            BANNER, "# Changelog", "",
            "Notable changes are recorded per merged PR.", "",
        ]),
    }


def generate(root: Path, out: Path, check: bool):
    """Write (or check) the doc set. Returns the list of files that differ."""
    stacks = detect_stack(root)
    docs = _doc_set(root, stacks)
    changed = []
    for name, body in docs.items():
        target = out / name
        body = body.rstrip() + "\n"
        current = target.read_text() if target.exists() else None
        if current != body:
            changed.append(name)
            if not check:
                out.mkdir(parents=True, exist_ok=True)
                target.write_text(body)
    return stacks, changed


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate/maintain project docs")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="docs")
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if docs are out of date; write nothing")
    args = parser.parse_args(argv)

    root, out = Path(args.root), Path(args.out)
    stacks, changed = generate(root, out, check=args.check)
    if not stacks:
        print("no source stack detected — generated notes-based architecture", file=sys.stderr)
    if args.check:
        if changed:
            print(f"docs out of date: {', '.join(changed)}", file=sys.stderr)
            return 1
        print("docs up to date", file=sys.stderr)
        return 0
    print(f"generated/updated: {', '.join(changed) if changed else '(no changes)'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
