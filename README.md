# Agentic DevSecOps Pipeline

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/Somu60789/DevSecOps/actions/workflows/ci.yml/badge.svg)](https://github.com/Somu60789/DevSecOps/actions/workflows/ci.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

An end-to-end, **agentic** DevSecOps pipeline any team can adopt by referencing a
few reusable GitHub Actions workflows — no implementation copied into your repo.

> **scan → AI-triage → safe-auto-fix → optimize → continuous docs → one consolidated PR comment**, plus multi-stack build/test, Checkmarx SAST remediation, and a gated deploy.

Deterministic scanners produce ground truth; an AI agent triages, explains, fixes
the unambiguously-safe issues, and proposes the rest. **Humans stay in the loop**:
the agent opens PRs and never merges; deploys sit behind an environment approval.

## Why

Most teams bolt security tools onto CI one at a time and drown in raw findings.
This product gives you the whole loop as a single dependency:

- **Provider-agnostic AI** — point `AGENT_CMD` at any runtime (an AWS Bedrock +
  Claude adapter ships in the box). No vendor lock-in.
- **Works with what you have** — GitHub Actions *and* a Jenkins shared-library
  step for on-prem Checkmarx (CxSAST). Ingests SARIF and CxSAST XML.
- **Safe by default** — never pushes to your default branch, never force-pushes,
  auto-fixes only behavior-preserving classes, and degrades to raw findings if
  the AI is unavailable.

## Quick start

Copy [`examples/caller-devsecops.yml`](examples/caller-devsecops.yml) into your
repo as `.github/workflows/devsecops.yml`:

```yaml
name: DevSecOps
on: [push, pull_request]
jobs:
  devsecops:
    uses: Somu60789/DevSecOps/.github/workflows/reusable-devsecops.yml@v1
    secrets: inherit
```

That's the whole integration. See **[USAGE.md](USAGE.md)** for every workflow,
input, and secret.

## What's included

| Capability | Reusable workflow |
|------------|-------------------|
| Everything, toggleable | `reusable-devsecops.yml` |
| Security scanners → normalized findings | `reusable-security.yml` |
| AI triage + safe auto-fix | `reusable-agent-fix.yml` |
| Consolidated PR review comment | `reusable-review.yml` |
| Continuous documentation | `reusable-docs.yml` |
| Checkmarx scan → remediation PR | `reusable-checkmarx-remediate.yml` |
| Gradle / Node / Python build + multi-registry publish | `reusable-build-gradle.yml`, `reusable-build-node.yml`, `reusable-build-python.yml` |
| Multi-stack tests + coverage gate | `reusable-test.yml` |
| Gated deploy (environment approval) | `reusable-deploy.yml` |

Scanners: gitleaks (secrets), Semgrep + Checkmarx (SAST), Trivy (SCA/license/
container), Checkov (IaC), lizard/jscpd (clean-code).

## Versioning

Pin `@v1` for non-breaking updates, or `@v1.x.y` for an exact version. See
[releases](https://github.com/Somu60789/DevSecOps/releases).

## Contributing

Contributions are welcome from everyone — see [CONTRIBUTING.md](CONTRIBUTING.md)
and our [Code of Conduct](CODE_OF_CONDUCT.md). To report a vulnerability, see
[SECURITY.md](SECURITY.md).

## License

[Apache License 2.0](LICENSE) — free for any company to use, modify, and
distribute, including in proprietary pipelines.
