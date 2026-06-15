#!/usr/bin/env bash
# Portable agent entry point — runs identically in CI and locally.
#
# Usage:
#   run-agent.sh <stage> <findings.json> [--out <file>]
#
#   stage         one of: triage | fix | optimize
#   findings.json normalized scanner output (from collect-findings.py)
#
# The agent runtime is provider-agnostic and configured via environment, so no
# specific tool is hardcoded here:
#   AGENT_CMD   command that reads a prompt on stdin and writes the result to
#               stdout (default: "agent --print"). Override to point at whatever
#               runtime is installed in the environment.
#   AGENT_RETRIES   max attempts on failure (default: 3)
#   AGENT_BACKOFF   base seconds for exponential backoff (default: 2)
#
# On persistent agent failure the script exits non-zero AFTER writing a fallback
# marker file, so callers can degrade to raw scanner output (security visibility
# must never depend on the agent being up).

set -euo pipefail

PROMPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.github/agent/prompts" && pwd)"
AGENT_CMD="${AGENT_CMD:-agent --print}"
AGENT_RETRIES="${AGENT_RETRIES:-3}"
AGENT_BACKOFF="${AGENT_BACKOFF:-2}"

die() { echo "run-agent: $*" >&2; exit 2; }

[ $# -ge 2 ] || die "usage: run-agent.sh <triage|fix|optimize|fix-all> <findings.json> [--out <file>]"

STAGE="$1"; FINDINGS="$2"; shift 2
OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    *) die "unknown argument: $1" ;;
  esac
done

case "$STAGE" in
  triage|fix|optimize|fix-all) ;;
  *) die "invalid stage: $STAGE (expected triage|fix|optimize|fix-all)" ;;
esac

PROMPT_FILE="$PROMPT_DIR/$STAGE.md"
[ -f "$PROMPT_FILE" ] || die "missing prompt: $PROMPT_FILE"
[ -f "$FINDINGS" ] || die "missing findings file: $FINDINGS"

OUT="${OUT:-agent-$STAGE.json}"

# Assemble the full prompt: stage instructions + findings + diff context.
build_input() {
  cat "$PROMPT_FILE"
  echo
  echo "## findings.json"
  echo '```json'
  cat "$FINDINGS"
  echo '```'
  echo
  echo "## diff (against base)"
  echo '```diff'
  git diff "${BASE_REF:-origin/master}"...HEAD 2>/dev/null || git diff HEAD~1 2>/dev/null || echo "(no diff available)"
  echo '```'
}

attempt=1
while [ "$attempt" -le "$AGENT_RETRIES" ]; do
  echo "run-agent: stage=$STAGE attempt=$attempt/$AGENT_RETRIES" >&2
  if build_input | $AGENT_CMD > "$OUT" 2>/tmp/agent-err.log; then
    if [ -s "$OUT" ]; then
      echo "run-agent: wrote $OUT" >&2
      exit 0
    fi
    echo "run-agent: empty output, retrying" >&2
  else
    echo "run-agent: agent command failed:" >&2
    cat /tmp/agent-err.log >&2 || true
  fi
  sleep_for=$(( AGENT_BACKOFF ** attempt ))
  echo "run-agent: backing off ${sleep_for}s" >&2
  sleep "$sleep_for"
  attempt=$(( attempt + 1 ))
done

# Persistent failure: emit a fallback marker so the caller can degrade to raw SARIF.
echo '{"agent_status":"failed","stage":"'"$STAGE"'","fallback":"use raw scanner findings"}' > "$OUT"
echo "run-agent: agent unavailable after $AGENT_RETRIES attempts; wrote fallback marker to $OUT" >&2
exit 1
