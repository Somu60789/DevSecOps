# Task 03 — Code-Fix Bot (Triage + Safe Auto-Fix + Optimize)

**Branch:** `bot/code-fix-YYYYMMDD`
**Subsystem:** 2 (AI agent stages 2–4)
**Depends on:** Task 02 (`findings.json` is the input).

## Goal

Consume `findings.json`, run the AI agent through triage → safe-auto-fix →
optimize, and land the safe fixes on a PR branch. The AI never replaces a
scanner: it triages ground truth, fixes only unambiguously-safe classes, and
proposes (never applies) logic/perf changes.

## Files

```
.github/workflows/ai-agent.yml    # orchestrates stages 2-4 (and 6, see Task 04)
scripts/run-agent.sh              # portable entry: runs in CI or locally
.github/agent/prompts/triage.md   # Stage 2 prompt
.github/agent/prompts/fix.md      # Stage 3 prompt
.github/agent/prompts/optimize.md # Stage 4 prompt
```

`run-agent.sh` takes a stage name + `findings.json` path and is the single entry
point both Actions and a local developer invoke. Agent logic lives in the
prompts + `config.yml`, not hardcoded in YAML.

## Stage 2 — Triage (AI)
Input: `findings.json` + PR diff. Output: structured verdicts:
```json
{ "id": "<finding id>", "verdict": "real|noise|needs-human",
  "severity": "<possibly adjusted>", "explanation": "why", "fixable_safely": true }
```
Rate-limit / API failure → retry with backoff; on persistent failure, skip
triage and fall back to raw SARIF (security visibility must not depend on the AI).

## Stage 3 — Safe Auto-Fix (AI)
**Only** these unambiguously-safe classes may be auto-applied and committed:
- Code formatting (prettier/black/gofmt — deterministic formatters)
- Unused imports / unused variables removal
- Lint auto-fixes that don't change behavior
- Simple secret removal (replace hardcoded secret with env-var reference +
  flag for rotation in the PR comment)

**Never auto-fix logic.** Anything ambiguous → leave for Stage 4 as a suggestion.
Commit message: `fix: <class> — <short description>` (no AI attribution).

## Stage 4 — Optimize (AI, suggestion-only)
Proposes algorithmic / allocation / query improvements. **Never auto-applied.**
- Safe-to-show suggestions → included in the PR review comment (Task 04).
- Risky changes → inserted as commented-out code with a `TODO:` explanation.

## Acceptance Criteria

- [ ] `run-agent.sh triage|fix|optimize <findings.json>` runs in CI and locally.
- [ ] Triage emits structured verdicts; falls back to raw SARIF on AI failure.
- [ ] Auto-fix touches only the four safe classes; a logic change is never committed.
- [ ] Hardcoded-secret fixes replace with env reference and flag rotation.
- [ ] Optimizer output is suggestion-only; risky items appear as `TODO:` comments.
- [ ] All commits land on the `bot/code-fix-YYYYMMDD` branch, never main/master.
- [ ] No AI/assistant attribution in commits, code, or comments.

## Safety

- When uncertain about a fix, raise the PR with the change commented out + `TODO:`.
- Never `--force`, never `--no-verify`.
- `actionlint` + dry-run on generated YAML before commit.
