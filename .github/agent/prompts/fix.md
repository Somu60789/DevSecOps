# Stage 3 — Safe Auto-Fix

You are given the triage verdicts (Stage 2) and the repository working tree.

Apply fixes **only** for findings where `verdict == "real"` AND
`fixable_safely == true`, and **only** within these unambiguously-safe classes:

1. **Formatting** — run the project's deterministic formatter (prettier, black,
   gofmt). Never hand-edit formatting.
2. **Unused imports / unused variables** — remove them.
3. **Behavior-preserving lint fixes** — only auto-fixes the linter itself marks
   as safe (e.g. `eslint --fix`, `ruff --fix`). Never a fix that changes output.
4. **Hardcoded secret removal** — replace the literal with a reference to an
   environment variable (e.g. `os.environ["X"]`), and record the secret's
   location in the rotation list (do NOT print the secret value).

**Never** change logic, control flow, algorithms, or output. If a fix is
tempting but touches behavior, leave it for Stage 4 (optimize) instead.

After applying fixes, output a JSON object and nothing else:

```json
{
  "applied": [
    {"id": "<finding id>", "class": "format|imports|lint|secret", "file": "path", "summary": "what changed"}
  ],
  "secrets_to_rotate": [
    {"file": "path", "line": 12, "note": "hardcoded credential replaced with env reference; rotate the live secret"}
  ],
  "skipped": [
    {"id": "<finding id>", "reason": "not a safe class / needs human"}
  ]
}
```

Commit message format (no attribution, no AI identity):
`fix: <class> — <short description>`

Do not include any identity or attribution text in code comments or output.
