# Task 04 — PR Review Bot (Consolidated Comment)

**Branch:** `bot/pr-review-setup`
**Subsystem:** 4 (AI agent stage 6)
**Depends on:** Task 02 (`findings.json`) + Task 03 (triage verdicts, optimize suggestions).

## Goal

Post exactly **one consolidated comment per commit** aggregating every category
of finding, plus a single top-level pass/fail summary comment per PR. Never post
multiple separate comments for the same commit.

## Files

```
.github/agent/prompts/review.md   # Stage 6 prompt: assemble the combined comment
scripts/post-review.py            # gh API: upsert one comment per commit
```

`post-review.py` is idempotent: re-running on the same commit **edits** the
existing bot comment (matched by a hidden marker) rather than adding a new one.
Marker: `<!-- bot-review:<commit-sha-short> -->`.

## Combined Comment Format (exact)

```
## Bot Review: <commit-sha-short>

### Documentation
- [ ] <finding or ✅ Pass>

### Security
- [ ] <finding or ✅ Pass>

### Code Quality
- [ ] <finding or ✅ Pass>

### Test Coverage
- [ ] <finding or ✅ Pass>

### Clean Code
- [ ] <finding or ✅ Pass>

---
**Overall:** ✅ Pass | ⚠️ Warnings: N | ❌ Failures: N
```

## Category Sources

| Section | Source |
|---------|--------|
| Documentation | Task 01 docs-gap check (missing/stale docs for changed code) |
| Security | `findings.json` categories: sast, sca, secret, container, iac, license |
| Code Quality | Optimizer suggestions (Task 03 Stage 4) |
| Test Coverage | Coverage delta vs base (if a coverage tool is present; else "n/a") |
| Clean Code | complexity > 10, fn length > 40, names < 3 chars, dead code, dup > 5%, print/console, TODO/FIXME > 30 days |

## Top-Level Summary Comment

One per PR (not per commit), upserted via marker `<!-- bot-summary -->`:

| Category | Status |
|----------|--------|
| Documentation | ✅/⚠️/❌ |
| Security | ✅/⚠️/❌ |
| Code Quality | ✅/⚠️/❌ |
| Test Coverage | ✅/⚠️/❌ |
| Clean Code | ✅/⚠️/❌ |

## Acceptance Criteria

- [ ] Exactly one comment per commit; re-runs edit, never duplicate.
- [ ] Comment follows the exact format above, all five sections present.
- [ ] Each section shows real findings or `✅ Pass`.
- [ ] Overall line counts warnings and failures correctly.
- [ ] One top-level summary comment per PR with the pass/fail table.
- [ ] `post-review.py` is idempotent (verified by re-running against a test PR).
- [ ] No AI/assistant attribution anywhere in the comment.

## Safety

- AI failure → post a degraded comment from raw `findings.json` so review still
  happens; note that triage was skipped.
- Never edit a human's comment; only upsert comments bearing the bot marker.
