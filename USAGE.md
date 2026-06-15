# DevSecOps Product — Usage

An end-to-end DevSecOps pipeline any repo can adopt by referencing reusable
workflows. Build, scan, AI-triage, safe-auto-fix, continuous docs, a single
consolidated PR review comment, Checkmarx SAST remediation, and a gated deploy —
without copying any of the implementation into your repo.

## Quick start (the whole product)

Copy [`examples/caller-devsecops.yml`](examples/caller-devsecops.yml) into your
repo as `.github/workflows/devsecops.yml`:

```yaml
jobs:
  devsecops:
    uses: Somu60789/DevSecOps/.github/workflows/reusable-devsecops.yml@v1
    secrets: inherit
```

That's it. On every push/PR you get build + scan + safe-fix + docs + the
consolidated review comment.

## Versioning

Pin `@v1` for non-breaking updates (the moving major tag), or `@v1.0.0` for an
exact pin. Keep the `product_ref` input in sync with the `@ref` you call at.

## Call workflows independently

Every capability is also a standalone reusable workflow — pick only what you need:

| Workflow | Purpose | Trigger context |
|----------|---------|-----------------|
| `reusable-devsecops.yml` | Everything, with per-stage toggles | push / PR / schedule |
| `reusable-build.yml` | Multi-stack build + test (node/python/java/go) + container | any |
| `reusable-security.yml` | Scanners → one `findings.json` | any |
| `reusable-agent-fix.yml` | Triage + safe auto-fix on the PR branch | pull_request |
| `reusable-docs.yml` | Docs-on-PR + nightly drift sweep | PR / schedule |
| `reusable-review.yml` | Consolidated PR review comment | pull_request |
| `reusable-checkmarx-remediate.yml` | Checkmarx scan → remediation PR | schedule / manual |
| `reusable-deploy.yml` | Gated deploy behind an Environment approval | tag / manual |

Example — security + review only:

```yaml
jobs:
  security:
    uses: Somu60789/DevSecOps/.github/workflows/reusable-security.yml@v1
    secrets: inherit
  review:
    needs: security
    uses: Somu60789/DevSecOps/.github/workflows/reusable-review.yml@v1
    with:
      triage_artifact: "" # no agent stage; review uses raw findings
    secrets: inherit
```

## Configuration

### Secrets (all optional unless a feature is used)

| Secret | Needed for |
|--------|-----------|
| `AGENT_API_KEY` | AI triage / fix / optimize / remediation |
| `CX_SERVER_URL`, `CX_USERNAME`, `CX_PASSWORD`, `CX_TEAM` | Checkmarx SAST |

### Variables

| Variable | Purpose |
|----------|---------|
| `AGENT_CMD` | Provider-agnostic agent runtime command (e.g. the CLI that reads a prompt on stdin). Without it, AI stages write a fallback marker and the review degrades to raw findings. |

If Checkmarx secrets are absent, the Checkmarx job auto-skips — the rest of the
pipeline runs unaffected.

## Deploy gate

Deploy is deliberately **not** chained into the end-to-end workflow. Use
`reusable-deploy.yml` and configure the target GitHub Environment's required
reviewers — the deploy pauses for human approval. Combined with the
PR-merge gate, these are the two human-in-the-loop checkpoints; everything else
is autonomous.

## How tooling is loaded

Reusable workflows run in **your** repo's context, so each one checks out this
product repo (at `product_ref`) into `._devsecops/` to get the scripts and the
Checkmarx composite action. Nothing is vendored into your repo.
