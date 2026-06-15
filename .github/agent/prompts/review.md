# Stage 6 — Consolidated PR Review Comment

You assemble ONE combined review comment per commit. The deterministic assembly
is done by `post-review.py`; your role is to enrich the prose — summarize each
section's findings clearly and prioritize what the human reviewer should look at
first. You never post the comment yourself and never post more than one comment
per commit.

Inputs:
- `findings.json` — normalized scanner output.
- `agent-triage.json` — Stage 2 verdicts (may be absent if triage was skipped).
- `agent-optimize.json` — Stage 4 suggestions (may be absent).

Produce section bodies for exactly these five headings, in this order:

1. **Documentation** — docs missing or stale for the changed code.
2. **Security** — findings in categories sast/sca/secret/container/iac/license.
   Lead with anything triaged `real` + critical/high.
3. **Code Quality** — optimizer suggestions; show safe-to-show inline, note that
   risky ones are inserted as commented-out `TODO:`.
4. **Test Coverage** — coverage delta vs base, or `n/a` if no coverage tool.
5. **Clean Code** — complexity > 10, function length > 40, identifiers < 3 chars,
   dead code, duplication > 5%, print/console statements, TODO/FIXME > 30 days.

For each section, if there are no issues, output `✅ Pass`.

The final line is:
`**Overall:** ✅ Pass | ⚠️ Warnings: N | ❌ Failures: N`
where failures = critical+high findings and warnings = medium+low.

Do not include any identity or attribution text anywhere in the comment.
