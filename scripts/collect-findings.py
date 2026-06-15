#!/usr/bin/env python3
"""Normalize heterogeneous scanner outputs into a single findings.json.

Reads the artifacts produced by the Stage 1 scanners (SARIF and tool-specific
JSON), maps them onto one schema, and writes the combined document. No scanner
output is allowed to abort the run: a missing or malformed file is recorded in
`summary.scanner_errors` and processing continues, so security visibility never
depends on every scanner succeeding.

Usage:
    collect-findings.py --inputs tool:category:path [tool:category:path ...] \\
        --out findings.json --generated-at <ISO8601>

`--generated-at` is injected (CI passes the workflow start time) rather than
computed in-process, to keep output reproducible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA_VERSION = "1"

# Map assorted scanner severity vocabularies onto a five-level scale.
_SEVERITY_MAP = {
    # generic
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "moderate": "medium",
    "low": "low",
    "info": "info",
    "informational": "info",
    "unknown": "info",
    # SARIF levels
    "error": "high",
    "warning": "medium",
    "note": "info",
    "none": "info",
}


def normalize_severity(value: str | None) -> str:
    """Return one of critical|high|medium|low|info for any scanner string."""
    if not value:
        return "info"
    return _SEVERITY_MAP.get(str(value).strip().lower(), "info")


def finding_id(tool: str, rule_id: str, file: str, line: int | None) -> str:
    """Stable hash of (tool, rule_id, file, line) so a finding dedupes across runs."""
    key = f"{tool}|{rule_id}|{file}|{line}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _make_finding(tool, category, severity, file, line, rule_id, message, raw):
    return {
        "id": finding_id(tool, rule_id, file, line),
        "tool": tool,
        "category": category,
        "severity": severity,
        "file": file,
        "line": line,
        "rule_id": rule_id,
        "message": message,
        "raw": raw,
    }


def _parse_sarif(data, tool, category):
    """Yield findings from a SARIF document (semgrep, codeql, trivy, checkov)."""
    out = []
    for run in data.get("runs", []):
        for res in run.get("results", []):
            rule_id = res.get("ruleId", "")
            level = res.get("level", "warning")
            message = (res.get("message") or {}).get("text", "")
            file, line = "", None
            locs = res.get("locations") or []
            if locs:
                phys = locs[0].get("physicalLocation", {})
                file = phys.get("artifactLocation", {}).get("uri", "")
                line = phys.get("region", {}).get("startLine")
            out.append(_make_finding(
                tool, category, normalize_severity(level),
                file, line, rule_id, message, res))
    return out


def _parse_gitleaks(data, tool, category):
    """Yield findings from gitleaks JSON (a list of secret hits). Always critical."""
    out = []
    for item in data:
        out.append(_make_finding(
            tool, category, "critical",
            item.get("File", ""), item.get("StartLine"),
            item.get("RuleID", ""), item.get("Description", ""),
            {k: v for k, v in item.items() if k != "Secret"}))  # never store the secret
    return out


def _parse_generic_list(data, tool, category):
    """Best-effort parser for tool JSON shaped as a list of finding-ish dicts."""
    out = []
    items = data if isinstance(data, list) else data.get("results", data.get("findings", []))
    for item in items or []:
        if not isinstance(item, dict):
            continue
        out.append(_make_finding(
            tool, category,
            normalize_severity(item.get("severity") or item.get("level")),
            item.get("file") or item.get("File") or item.get("path", ""),
            item.get("line") or item.get("StartLine") or item.get("start_line"),
            item.get("rule_id") or item.get("ruleId") or item.get("RuleID", ""),
            item.get("message") or item.get("Description") or item.get("description", ""),
            item))
    return out


def _dispatch(tool, category, data):
    if tool == "gitleaks":
        return _parse_gitleaks(data, tool, category)
    if isinstance(data, dict) and "runs" in data:
        return _parse_sarif(data, tool, category)
    return _parse_generic_list(data, tool, category)


def collect(inputs, generated_at):
    """Normalize every input descriptor into one findings document.

    `inputs` is a list of {"tool", "category", "path"} dicts.
    """
    findings = []
    scanner_errors = []
    seen_ids = set()

    for desc in inputs:
        tool, category, path = desc["tool"], desc["category"], desc["path"]
        try:
            raw_text = Path(path).read_text()
            data = json.loads(raw_text) if raw_text.strip() else []
        except FileNotFoundError:
            scanner_errors.append({"tool": tool, "error": "output not found", "path": path})
            continue
        except (json.JSONDecodeError, OSError) as exc:
            scanner_errors.append({"tool": tool, "error": str(exc), "path": path})
            continue

        for f in _dispatch(tool, category, data):
            if f["id"] in seen_ids:
                continue
            seen_ids.add(f["id"])
            findings.append(f)

    by_severity, by_category = {}, {}
    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        by_category[f["category"]] = by_category.get(f["category"], 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "findings": findings,
        "summary": {
            "by_severity": by_severity,
            "by_category": by_category,
            "scanner_errors": scanner_errors,
        },
    }


def _parse_input_arg(token):
    """Parse a 'tool:category:path' CLI token into a descriptor dict."""
    tool, category, path = token.split(":", 2)
    return {"tool": tool, "category": category, "path": path}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Normalize scanner outputs into findings.json")
    parser.add_argument("--inputs", nargs="*", default=[],
                        help="tool:category:path descriptors")
    parser.add_argument("--out", default="findings.json")
    parser.add_argument("--generated-at", required=True,
                        help="ISO8601 timestamp injected by the caller")
    args = parser.parse_args(argv)

    inputs = [_parse_input_arg(t) for t in args.inputs]
    result = collect(inputs=inputs, generated_at=args.generated_at)
    Path(args.out).write_text(json.dumps(result, indent=2))

    n = len(result["findings"])
    errs = len(result["summary"]["scanner_errors"])
    print(f"collected {n} findings, {errs} scanner errors -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
