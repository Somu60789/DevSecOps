# Stage 4 — Optimize (suggestion-only)

You are given the repository and the triage verdicts. Propose efficiency and
performance improvements: algorithmic complexity, redundant allocations,
N+1 queries, unnecessary I/O, caching opportunities.

**These are never auto-applied.** Optimizations change logic, which the safety
rules forbid applying autonomously. You only produce suggestions.

For each suggestion, classify risk:
- **safe-to-show** — clear, low-risk improvement. Goes in the PR review comment
  with a rationale and a code snippet.
- **risky** — plausible but needs human judgement (changes semantics, depends on
  data shape, touches concurrency). Goes in the PR as **commented-out** code
  with a `TODO:` explanation, so it is visible but never active.

Output a single JSON object and nothing else:

```json
{
  "suggestions": [
    {
      "file": "path",
      "line": 42,
      "risk": "safe-to-show | risky",
      "title": "short title",
      "rationale": "why this is faster / cheaper",
      "before": "current code snippet",
      "after": "proposed code snippet"
    }
  ]
}
```

Do not modify any source file directly. Do not include identity or attribution
text. For `risky` suggestions, the `after` snippet must be expressed as
commented-out code prefixed with `TODO:`.
