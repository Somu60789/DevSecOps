# Task 02 — DevSecOps CI/CD Pipeline (Stage 1 scanners)

**Branch:** `bot/devsecops-pipeline`
**Subsystem:** 1 (Scanner pipeline + findings normalization)
**Depends on:** task spec files (this set).

## Goal

Stand up the deterministic scanner layer: ground-truth security + clean-code
findings on every push/PR, emitted as SARIF and a single normalized JSON the AI
stages consume. **No AI in this layer** — scanners produce facts.

## Files

```
.github/workflows/devsecops.yml   # Stage 1 scanners, SARIF upload, artifact
scripts/collect-findings.py       # normalize all scanner outputs -> findings.json
.github/agent/config.yml          # tool toggles, severity thresholds, paths
tests/test_collect_findings.py    # unit tests for normalization
```

If `.github/workflows/devsecops.yml` already exists and is active, **do not
overwrite it** — write `devsecops-bot.yml` instead and note the conflict in the
PR body (per safety rules).

## Scan Stack

| Class | Tool | Output |
|-------|------|--------|
| SAST | CodeQL and/or Semgrep | SARIF |
| SCA / deps | Trivy (+ Dependabot config) | SARIF/JSON |
| Secrets | gitleaks | JSON |
| Container | Trivy image scan | SARIF |
| IaC | Checkov | SARIF |
| License | Trivy license / scancode | JSON |
| Clean-code: complexity | lizard (multi-lang) / radon (py) | JSON |
| Clean-code: duplication | jscpd | JSON |
| Clean-code: dead code | ts-prune (TS) / vulture (py) | text→JSON |

Each scanner runs as its own job/step with `continue-on-error: true` so one
failure never blocks the others. Stack auto-detection gates which run.

## `collect-findings.py` contract

Reads every scanner artifact, emits one `findings.json`:

```json
{
  "schema_version": "1",
  "generated_at": "<ISO8601 — injected, not computed in-process>",
  "findings": [
    {
      "id": "string-stable-hash",
      "tool": "gitleaks|trivy|semgrep|codeql|checkov|lizard|jscpd|vulture|...",
      "category": "sast|sca|secret|container|iac|license|complexity|duplication|deadcode",
      "severity": "critical|high|medium|low|info",
      "file": "path/relative/to/repo",
      "line": 123,
      "rule_id": "string",
      "message": "human-readable",
      "raw": { }
    }
  ],
  "summary": { "by_severity": {}, "by_category": {}, "scanner_errors": [] }
}
```

- Missing/empty scanner output → record in `summary.scanner_errors`, continue.
- Severity strings normalized to the five-level scale above.
- `id` is a stable hash of (tool, rule_id, file, line) so the same finding
  dedupes across runs.

## Acceptance Criteria

- [ ] `devsecops.yml` validates with `actionlint`.
- [ ] Each scanner job is `continue-on-error` and uploads SARIF to code scanning.
- [ ] A single `findings.json` artifact is produced and uploaded.
- [ ] `collect-findings.py` has unit tests covering: empty input, one finding per
      category, severity normalization, scanner-error capture, stable `id` hash.
- [ ] Stack detection skips irrelevant scanners (e.g. no ts-prune without TS).
- [ ] No secrets, tokens, or `.env` committed; gitleaks runs against the repo.

## Safety

- Validate YAML with `actionlint` + dry-run before commit.
- Never push to main/master; PR only.
- Pin third-party actions to a commit SHA or major version tag.
