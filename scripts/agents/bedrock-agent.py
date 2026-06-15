#!/usr/bin/env python3
"""Bedrock + Claude agent adapter — a concrete AGENT_CMD for run-agent.sh.

run-agent.sh is provider-agnostic: it pipes a fully-assembled prompt on stdin to
whatever `AGENT_CMD` names and reads the result from stdout. This adapter is one
such command, backed by AWS Bedrock (matching the org's existing
bedrock-pr-review setup). Wire it with:

    export AGENT_CMD="python3 scripts/agents/bedrock-agent.py"

Environment:
    MODEL_ID    Bedrock model id (default: us.anthropic.claude-sonnet-4-6)
    AWS_REGION  region where Bedrock is available (default: us-east-1)
    MAX_TOKENS  response cap (default: 8192)
    AWS credentials are picked up from the standard chain (env / role / profile).

Stdin: the prompt. Stdout: the model's text response (the agent stages expect
JSON in that text per their prompt instructions). Exit non-zero on failure so
run-agent.sh retries with backoff and ultimately falls back to raw findings.
"""
from __future__ import annotations

import os
import sys

DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-6"
DEFAULT_REGION = "us-east-1"
DEFAULT_MAX_TOKENS = 8192


def run(prompt: str, *, model_id: str, region: str, max_tokens: int) -> str:
    """Call Claude on Bedrock with a single user message and return the text."""
    import boto3  # imported lazily so --help / import works without boto3

    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
    )
    parts = response["output"]["message"]["content"]
    return "".join(p.get("text", "") for p in parts)


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    prompt = sys.stdin.read()
    if not prompt.strip():
        print("bedrock-agent: empty prompt on stdin", file=sys.stderr)
        return 2

    model_id = os.environ.get("MODEL_ID", DEFAULT_MODEL)
    region = os.environ.get("AWS_REGION", DEFAULT_REGION)
    try:
        max_tokens = int(os.environ.get("MAX_TOKENS", DEFAULT_MAX_TOKENS))
    except ValueError:
        max_tokens = DEFAULT_MAX_TOKENS

    try:
        text = run(prompt, model_id=model_id, region=region, max_tokens=max_tokens)
    except Exception as exc:  # surface any Bedrock/credential error to run-agent.sh
        print(f"bedrock-agent: call failed: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
