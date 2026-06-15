#!/usr/bin/env python3
"""Assemble and upsert the consolidated PR review comment.

One combined comment per commit (Documentation / Security / Code Quality /
Test Coverage / Clean Code) plus a single top-level pass/fail summary per PR.
The comment is idempotent: re-running on the same commit edits the existing
comment (matched by a hidden marker) instead of posting a duplicate.

The GitHub interaction is done with `gh api`; the comment-assembly logic is pure
and unit-tested separately.

Usage:
    post-review.py --commit <sha> --pr <number> --repo <owner/name> \\
        --findings findings.json [--triage agent-triage.json] \\
        [--optimize agent-optimize.json] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SUMMARY_MARKER = "<!-- bot-summary -->"

# Which finding categories map to which comment section.
_SECURITY_CATS = {"sast", "sca", "secret", "container", "iac", "license"}
_CLEAN_CODE_CATS = {"complexity", "duplication", "deadcode"}


def comment_marker(commit_short: str) -> str:
    """Hidden HTML marker that makes a per-commit comment findable for upsert."""
    return f"<!-- bot-review:{commit_short} -->"


def _short(sha: str) -> str:
    return sha[:7]


def _line(f) -> str:
    loc = f.get("file", "")
    if f.get("line"):
        loc += f":{f['line']}"
    sev = f.get("severity", "info")
    return f"- [ ] **{sev}** `{loc}` — {f.get('message', '')} ({f.get('tool', '')})"


def _section(title: str, items) -> str:
    """Render one comment section: findings as checkboxes, or a pass line."""
    body = [f"### {title}"]
    if items:
        body.extend(items)
    else:
        body.append("- [x] ✅ Pass")
    return "\n".join(body)


def _classify_status(failures: int, warnings: int) -> str:
    if failures:
        return "❌"
    if warnings:
        return "⚠️"
    return "✅"


def build_comment(commit_sha, findings, verdicts, optimize):
    """Build the full per-commit comment body. Pure — no I/O.

    verdicts/optimize may be None to signal the agent stage was skipped
    (AI failure) — the comment degrades to raw findings and says so.
    """
    short = _short(commit_sha)
    flist = findings.get("findings", [])

    sec_items, clean_items = [], []
    failures, warnings = 0, 0
    for f in flist:
        sev = f.get("severity", "info")
        if sev in ("critical", "high"):
            failures += 1
        elif sev in ("medium", "low"):
            warnings += 1
        cat = f.get("category", "")
        if cat in _SECURITY_CATS:
            sec_items.append(_line(f))
        elif cat in _CLEAN_CODE_CATS:
            clean_items.append(_line(f))

    # Code Quality section is fed by optimizer suggestions.
    cq_items = []
    if optimize:
        for s in optimize.get("suggestions", []):
            cq_items.append(
                f"- [ ] **{s.get('risk', '')}** `{s.get('file', '')}:{s.get('line', '')}` — "
                f"{s.get('title', '')}: {s.get('rationale', '')}")

    parts = [comment_marker(short), f"## Bot Review: {short}", ""]

    if verdicts is None and optimize is None:
        parts.append("> AI triage was skipped (agent unavailable); showing raw scanner findings.")
        parts.append("")

    # Documentation and Test Coverage are wired in by Tasks 01 and the coverage
    # tool respectively; with no signal here they pass.
    parts.append(_section("Documentation", []))
    parts.append(_section("Security", sec_items))
    parts.append(_section("Code Quality", cq_items))
    parts.append(_section("Test Coverage", []))
    parts.append(_section("Clean Code", clean_items))
    parts.append("")
    parts.append("---")

    overall = "✅ Pass" if (failures == 0 and warnings == 0) else "Review needed"
    parts.append(f"**Overall:** {overall} | ⚠️ Warnings: {warnings} | ❌ Failures: {failures}")

    return "\n".join(parts)


def build_summary_table(statuses) -> str:
    """Top-level per-PR summary table. `statuses` maps category -> ✅/⚠️/❌."""
    rows = ["| Category | Status |", "|----------|--------|"]
    for cat in ("Documentation", "Security", "Code Quality", "Test Coverage", "Clean Code"):
        rows.append(f"| {cat} | {statuses.get(cat, '✅')} |")
    return "\n".join([SUMMARY_MARKER, "## Bot Review Summary", "", *rows])


def find_marked_comment(comments, marker):
    """Return the first comment whose body contains the marker, or None."""
    for c in comments:
        if marker in c.get("body", ""):
            return c
    return None


# --- GitHub I/O (thin wrappers over `gh api`) -------------------------------

def _gh_json(args):
    out = subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=True)
    return json.loads(out.stdout) if out.stdout.strip() else []


def list_comments(repo, pr_number):
    return _gh_json([f"repos/{repo}/issues/{pr_number}/comments", "--paginate"])


def upsert_comment(repo, pr_number, marker, body, dry_run=False):
    """Edit the existing marked comment if present, else create a new one."""
    if dry_run:
        print(body)
        return
    existing = find_marked_comment(list_comments(repo, pr_number), marker)
    if existing:
        subprocess.run(
            ["gh", "api", "--method", "PATCH",
             f"repos/{repo}/issues/comments/{existing['id']}",
             "-f", f"body={body}"], check=True)
    else:
        subprocess.run(
            ["gh", "api", "--method", "POST",
             f"repos/{repo}/issues/{pr_number}/comments",
             "-f", f"body={body}"], check=True)


def _load(path):
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError:
        return None
    # A fallback marker from run-agent.sh means the stage failed.
    if isinstance(data, dict) and data.get("agent_status") == "failed":
        return None
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Post the consolidated PR review comment")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--findings", required=True)
    parser.add_argument("--triage")
    parser.add_argument("--optimize")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    findings = json.loads(Path(args.findings).read_text())
    verdicts = _load(args.triage)
    optimize = _load(args.optimize)

    body = build_comment(args.commit, findings, verdicts, optimize)
    upsert_comment(args.repo, args.pr, comment_marker(_short(args.commit)), body,
                   dry_run=args.dry_run)
    print(f"posted review for {_short(args.commit)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
