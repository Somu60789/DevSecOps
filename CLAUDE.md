# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is a **product**, not an application: a library of reusable GitHub Actions
workflows (plus a Jenkins shared-library variant) that any team adopts by
*referencing* — nothing is vendored into the caller's repo. The pipeline is
`scan → AI-triage → safe-auto-fix → optimize → continuous docs → one consolidated
PR comment`, plus multi-stack build/test, Checkmarx SAST remediation, and a gated
deploy.

Two distinct audiences for any change:
- **Callers** consume the `reusable-*.yml` workflows via `uses:` (see `examples/`).
- **This repo's own CI** (`ci.yml`) tests the product itself — it is *not* a
  reusable workflow.

## Commands

```bash
# Run the full unit-test suite (mirrors ci.yml)
pytest tests/ -q

# Run a single test file / test
pytest tests/test_collect_findings.py -q
pytest tests/test_collect_findings.py::test_name -q

# Lint workflows and shell scripts (same tools as CI)
actionlint -color                      # all .github/workflows/*.yml
shellcheck --severity=error scripts/*.sh

# Run the agent loop locally (provider-agnostic; see "Agent runtime" below)
scripts/run-agent.sh <triage|fix|optimize|fix-all> findings.json --out agent-<stage>.json
```

A `.venv/` exists with pytest/pyyaml; the only test deps are `pytest` and `pyyaml`.

## Architecture

### The reusable-workflow layer (`.github/workflows/`)

`reusable-devsecops.yml` is the umbrella: it chains `reusable-build`,
`reusable-security`, `reusable-agent-fix`, `reusable-docs`, and `reusable-review`,
each gated by an `enable_*` boolean input. **Deploy is intentionally NOT chained
here** — `reusable-deploy.yml` is separate so a release always sits behind a
GitHub Environment approval. Each capability is also independently callable.

Because reusable workflows execute in the *caller's* repo context, every one of
them checks this product repo out into `._devsecops/` (at the `product_ref`
input) to get the scripts and composite actions. Keep `product_ref` in sync with
the `@ref` callers pin. Stack auto-detection (`reusable-build.yml` `detect` job)
gates stack-specific jobs by probing for `package.json` / `requirements.txt` /
`pom.xml|build.gradle` / `go.mod` / `Dockerfile`.

### The script layer (`scripts/`) — the actual logic

Workflows are thin; the testable logic lives in Python/bash here:

- `collect-findings.py` — normalizes heterogeneous scanner output (SARIF **and**
  Checkmarx CxSAST XML, plus tool JSON) into one `findings.json` on a single
  schema. A missing/malformed scanner file is recorded in
  `summary.scanner_errors` and never aborts the run — **security visibility must
  not depend on every scanner succeeding.** Finding IDs are stable hashes of
  `(tool, rule_id, file, line)` so findings dedupe across runs.
- `run-agent.sh` — provider-agnostic agent entry point. Assembles
  `prompt + findings.json + git diff` and pipes it to `$AGENT_CMD` (stdin→stdout)
  with retry/backoff. On persistent failure it writes a `{"agent_status":"failed",...}`
  fallback marker **then exits non-zero**, so callers degrade to raw findings.
- `post-review.py` — assembles and **upserts** the consolidated PR comment
  (idempotent via a hidden marker; one combined comment per commit + one
  top-level PR summary). GitHub I/O via `gh api`; assembly logic is pure/tested.
- `check-coverage.py` — parses Cobertura or JaCoCo XML, exits non-zero below the
  threshold (powers `reusable-test.yml`'s `min_coverage` gate).
- `gen-docs.py` — owns stack detection, the doc maintenance banner, and the
  architecture doc, including the notes-only fallback when no source stack exists.
  `--check` exits non-zero if regeneration would change anything (nightly drift PR).
- `summarize-remediation.py` — formats `fix-all` agent output into a PR-body
  summary. Pure formatting.
- `scripts/agents/bedrock-agent.py` — a concrete `AGENT_CMD` adapter (AWS Bedrock
  + Claude); one example of the provider-agnostic contract, not a hard dependency.

### Agent runtime contract

The agent is configured entirely via environment, never hardcoded:
- `AGENT_CMD` — any command reading a prompt on stdin, writing the response to
  stdout. Without it set, AI stages write a fallback marker and review degrades
  to raw findings.
- Stages are `triage | fix | optimize | fix-all`; each maps to a prompt in
  `.github/agent/prompts/<stage>.md`.
- `.github/agent/config.yml` is the single source of truth for scanner toggles,
  severity thresholds, and clean-code limits — edit there, **not** in workflow YAML.

### Jenkins path (`jenkins/`)

For on-prem Checkmarx estates: `remediateCheckmarx.groovy` fetches the CxSAST XML
report over REST, normalizes it with the *same* `collect-findings.py`, runs
`run-agent.sh fix-all`, and raises a remediation PR. Same agent loop, no GitHub
Actions required.

## Conventions specific to this repo

- **Hyphenated Python module names** (`collect-findings.py`) are not importable
  normally; tests load them via `importlib.util.spec_from_file_location` (see the
  top of any `tests/test_*.py`). Follow that pattern for new scripts/tests.
- `collect-findings.py` takes `--generated-at` as an injected ISO8601 value
  (CI passes the workflow start time) rather than calling the clock in-process —
  keep output reproducible; don't reintroduce wall-clock calls.
- **Never modify a workflow that's in active use in place** — per the safety
  rules, add a new file with a `-bot` suffix and flag the conflict in the PR.
- Docs under `docs/` carry a "maintained by the docs agent — edits may be
  overwritten" banner; edit the generator/source, not the rendered doc.
- `Rajiv.txt` is the seed "notes" file that drives `gen-docs.py`'s notes-only
  fallback when no source stack is present — it is referenced by name in tests.
