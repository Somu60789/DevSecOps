# Contributing

Thanks for your interest in improving the Agentic DevSecOps Pipeline! This
project is built to be used by any company, and contributions of all kinds are
welcome — bug reports, docs, new scanners, new stack support, and fixes.

## Ground rules

- Be respectful — see the [Code of Conduct](CODE_OF_CONDUCT.md).
- Open an issue before large changes so we can agree on the approach.
- Keep PRs focused: one logical change per PR.

## Development setup

The product's own logic is Python with a small test suite.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install pytest pyyaml
pytest -q
```

Workflows are validated with [actionlint](https://github.com/rhysd/actionlint):

```bash
bash <(curl -sSL https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash)
./actionlint
```

CI runs both on every PR (`.github/workflows/ci.yml`).

## Making a change

1. Fork and create a branch (`feat/...`, `fix/...`, or `docs/...`).
2. **Add or update tests.** Logic changes need test coverage; scripts live in
   `scripts/` with tests in `tests/`.
3. Run `pytest -q` and `actionlint` locally — both must pass.
4. Open a PR using the template. Describe what changed and why.

## What to expect

- A maintainer reviews every PR. The repo's own bot pipeline may also post a
  consolidated review comment.
- We squash-merge. Write a clear PR title — it becomes the commit message.

## Design principles (please preserve these)

- **Human-in-the-loop:** never push to a default branch, never merge, never
  deploy autonomously.
- **Safe-by-default fixes:** auto-fix only behavior-preserving classes; anything
  riskier is a suggestion or a gated remediation PR.
- **Provider-agnostic:** AI runtime is configured via `AGENT_CMD`; never hardcode
  a specific vendor.
- **Degrade gracefully:** a scanner or the AI being down must not break the
  pipeline — fall back to raw findings.

## License of contributions

By contributing, you agree that your contributions are licensed under the
project's [Apache License 2.0](LICENSE).
