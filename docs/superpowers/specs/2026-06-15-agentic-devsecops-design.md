# Agentic DevSecOps System — Design

**Date:** 2026-06-15
**Status:** Approved (design phase)

## Summary

A portable AI agent core that runs a full DevSecOps loop with minimal human
intervention while keeping a human in the loop for approvals. Deployed primarily
on GitHub Actions, but the agent logic is portable enough to run locally.

The loop, on every push/PR:

> **scan → AI-triage → safe-auto-fix → optimize-suggest → continuous-docs → one consolidated PR comment**

Deterministic scanners produce ground-truth findings; the AI agent (Claude)
triages, explains, and authors fixes/docs/suggestions. Everything the agent
produces lands in a branch + PR. The agent never pushes to `main`, never merges,
never deploys on its own.

## Human-in-the-Loop Gates

Two gates. The agent runs autonomously up to each, then waits.

1. **PR merge (always)** — agent opens PRs; a human reviews and merges. Baseline,
   non-negotiable.
2. **Deploy / release** — any deploy step sits behind a GitHub Environment
   protection rule requiring a designated reviewer's approval.

All other work (scanning, triage, safe auto-fixes, doc updates, posting review
comments) is autonomous.

## Architecture

```
Triggers: push | pull_request | schedule | manual
   |
   v
Stage 1: Deterministic scanners (no AI) -> SARIF + JSON findings
   |
   v
Stage 2: AI agent (Claude) -> triage, explain, author fixes/docs/suggestions
   |
   v
Stage 3: Human gates -> PR merge (always) + Deploy (Environment approval)
```

**Key principle:** the AI never replaces a scanner. Scanners produce ground
truth; the AI triages and explains them and authors fixes, docs, and
optimization suggestions.

## Agent Stages

| # | Stage | AI? | Output |
|---|-------|-----|--------|
| 1 | **Scan** — CodeQL/Semgrep (SAST), Trivy (SCA + container), gitleaks (secrets), Checkov (IaC), lizard/radon + jscpd (clean-code) | No | SARIF / JSON findings |
| 2 | **Triage** — reads findings + diff, marks real vs noise, assigns severity, explains each | Yes | structured verdicts |
| 3 | **Auto-fix** — only unambiguously-safe classes (formatting, unused imports, lint, simple secret removal) committed to the PR branch | Yes | commits on branch |
| 4 | **Optimize** — proposes efficiency/perf improvements (algorithmic, allocations, queries). **Never auto-applied** — posted as PR suggestions with rationale; risky ones as commented-out `TODO:` | Yes | PR suggestions |
| 5 | **Docs (continuous)** — on every code change, regenerate/patch affected docs in the same PR; nightly sweep opens a standalone `bot/docs-update` PR for anything missed | Yes | docs commits |
| 6 | **Review comment** — ONE consolidated comment per commit (Documentation / Security / Code Quality / Test Coverage / Clean Code) plus a top-level pass/fail summary | Yes | PR comment |

### Continuous documentation

Two cooperating modes so code and docs never drift:
- **Per-PR:** docs for changed code are updated inside the same PR.
- **Scheduled sweep:** a nightly job catches misses and opens `bot/docs-update`.

### Optimizer

Suggestion-only by design. Optimizations change logic, so per the safety rules
they are never auto-applied — they appear in the PR comment, and risky ones are
inserted as commented-out code with a `TODO:` explanation.

## Scan Stack

Full DevSecOps suite + clean-code baseline:
- **SAST:** CodeQL and/or Semgrep
- **SCA / dependencies:** Trivy + Dependabot
- **Secrets:** gitleaks
- **Container:** Trivy
- **IaC:** Checkov
- **License check**
- **Clean-code baseline:** lizard/radon (complexity), jscpd (duplication),
  dead-code (ts-prune/vulture), print/console detection, stale TODO/FIXME

## Repo Layout

```
.claude/
  tasks/
    01-documentation.md         # continuous docs agent spec
    02-devsecops-pipeline.md    # CI/CD pipeline spec
    03-code-fix-bot.md          # scan + triage + auto-fix + optimize spec
    04-pr-review-bot.md         # consolidated PR review spec
.github/
  workflows/
    devsecops.yml               # Stage 1 scanners (SARIF upload)
    ai-agent.yml                # Stages 2-6 (Claude, gated)
    docs-continuous.yml         # docs-on-push + nightly sweep
    deploy.yml                  # deploy job behind Environment approval
  agent/
    prompts/                    # versioned prompts per stage
    config.yml                  # tool toggles, severity thresholds, paths
scripts/
  run-agent.sh                  # portable entry — works in CI or locally
  collect-findings.py           # normalize scanner outputs -> one JSON
docs/
  (auto-generated, kept in sync)
```

The `scripts/` + `prompts/` + `config.yml` form the portability layer: GitHub
Actions calls them, and the same entry point runs locally. Agent logic lives in
prompts and config, not hardcoded in YAML.

## Error Handling

- **Scanner failure** — reported in the PR comment; does not block other
  scanners (non-fatal status, explicit reporting).
- **AI / API failure or rate limit** — retry with backoff; if still failing,
  post a comment that triage was skipped and fall back to raw scanner SARIF, so
  security visibility never depends on the AI being up.
- **YAML/config generation** — validated with `actionlint` + dry-run before any
  commit.

## Safety Rails (enforced)

- Never push to `main`/`master`; always a new branch.
- Branch naming: `bot/docs-update`, `bot/devsecops-pipeline`,
  `bot/code-fix-YYYYMMDD`, `bot/pr-review-setup`.
- Never `--force`, never `--no-verify`.
- Never commit secrets, tokens, `.env`, or credentials.
- Never auto-fix logic — only unambiguously-safe classes.
- Changes to existing active `.github/workflows/` are flagged in a PR comment,
  not applied; new files conflicting at a target path get a `-bot` suffix.
- No AI/assistant attribution in any committed artifact, commit message, PR, or
  comment (per global instructions).

## Testing

- Validate every generated YAML with `actionlint` + dry-run before commit.
- Unit tests for `collect-findings.py` (scanner-output normalization).
- Use the `Rajiv.txt` notes as a tiny seed example project to exercise the full
  scan → triage → fix → docs → comment flow end-to-end.

## Out of Scope (YAGNI)

- Auto-merging PRs.
- Auto-applying optimizations or any logic changes.
- Autonomous deploys (deploy is always gated).
- Building the autonomous-vehicle stack described in `Rajiv.txt` — that file is
  only the example repo the system operates on.
