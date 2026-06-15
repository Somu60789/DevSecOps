#!/usr/bin/env python3
"""Turn the fix-all agent output into a human-readable PR-body summary.

Reads the JSON produced by `run-agent.sh fix-all` and emits a short markdown
summary (counts, a per-finding table, secrets to rotate, unresolved items) used
in the remediation PR body. Pure formatting — no I/O beyond reading the file.

Usage:
    summarize-remediation.py <agent-fix-all.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def summarize(data) -> str:
    """Build the markdown summary from a fix-all result dict."""
    # run-agent.sh writes this marker when the agent never succeeded.
    if isinstance(data, dict) and data.get("agent_status") == "failed":
        return ("The remediation agent could not complete (it failed after "
                "retries). No automated fixes were applied; review the raw "
                "Checkmarx report.")

    remediated = data.get("remediated", []) if isinstance(data, dict) else []
    secrets = data.get("secrets_to_rotate", []) if isinstance(data, dict) else []
    unresolved = data.get("unresolved", []) if isinstance(data, dict) else []

    risky = sum(1 for r in remediated if r.get("confidence") == "risky")
    confident = len(remediated) - risky

    lines = ["## Remediation summary", ""]
    lines.append(
        f"Remediated **{len(remediated)} finding(s)** "
        f"({confident} confident, {risky} risky). "
        f"{len(unresolved)} unresolved.")
    lines.append("")

    if remediated:
        lines += ["| Vulnerability | File | Confidence | Change |",
                  "|---------------|------|------------|--------|"]
        for r in remediated:
            loc = r.get("file", "")
            if r.get("line"):
                loc += f":{r['line']}"
            lines.append(
                f"| {r.get('vulnerability', '')} | `{loc}` | "
                f"{r.get('confidence', '')} | {r.get('summary', '')} |")
        lines.append("")

    if secrets:
        lines += ["### Secrets to rotate", ""]
        for s in secrets:
            loc = s.get("file", "")
            if s.get("line"):
                loc += f":{s['line']}"
            lines.append(f"- `{loc}` — {s.get('note', 'rotate the live secret')}")
        lines.append("")

    if unresolved:
        lines += ["### Unresolved (need human attention)", ""]
        for u in unresolved:
            lines.append(f"- `{u.get('id', '')}` — {u.get('reason', '')}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: summarize-remediation.py <agent-fix-all.json>", file=sys.stderr)
        return 2
    path = Path(argv[0])
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        print("No machine-readable remediation summary available; see changed files.")
        return 0
    print(summarize(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
