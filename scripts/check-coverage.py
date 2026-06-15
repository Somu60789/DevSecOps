#!/usr/bin/env python3
"""Enforce a coverage threshold from a coverage report.

Parses a coverage XML report (Cobertura — coverage.py / nyc / gocover-cobertura;
or JaCoCo — Gradle/Java) and compares the line-coverage percentage against a
configurable minimum. Exits non-zero when below the minimum so a CI job fails.

Usage:
    check-coverage.py --file coverage.xml --min 80
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_coverage(path: str) -> float:
    """Return line-coverage as a percentage (0-100) from a Cobertura or JaCoCo XML."""
    root = ET.parse(path).getroot()

    # Cobertura: <coverage line-rate="0.87" ...>
    if root.tag == "coverage" and root.get("line-rate") is not None:
        return float(root.get("line-rate")) * 100.0

    # JaCoCo: top-level <counter type="LINE" missed=".." covered="..">
    for counter in root.findall("counter"):
        if counter.get("type") == "LINE":
            missed = int(counter.get("missed", "0"))
            covered = int(counter.get("covered", "0"))
            total = missed + covered
            return (covered / total * 100.0) if total else 100.0

    raise ValueError(f"unrecognized coverage report format: {path}")


def meets_threshold(coverage: float, minimum: float) -> bool:
    """True if coverage is at or above the minimum."""
    return coverage + 1e-9 >= minimum


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Enforce a coverage threshold")
    parser.add_argument("--file", required=True, help="coverage XML report")
    parser.add_argument("--min", type=float, default=0.0,
                        help="minimum line-coverage percentage (0-100)")
    args = parser.parse_args(argv)

    if not Path(args.file).exists():
        if args.min <= 0:
            print(f"coverage: no report at {args.file}; threshold is 0, skipping", file=sys.stderr)
            return 0
        print(f"coverage: report not found at {args.file}; required >= {args.min}%", file=sys.stderr)
        return 1

    try:
        coverage = parse_coverage(args.file)
    except (ET.ParseError, ValueError) as exc:
        print(f"coverage: could not parse {args.file}: {exc}", file=sys.stderr)
        return 1

    print(f"coverage: {coverage:.2f}% (minimum {args.min:.2f}%)")
    if not meets_threshold(coverage, args.min):
        print(f"coverage: FAILED — {coverage:.2f}% is below the {args.min:.2f}% threshold",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
