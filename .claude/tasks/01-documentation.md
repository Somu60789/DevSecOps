# Task 01 — Continuous Documentation Agent

**Branch:** `bot/docs-update`
**Subsystem:** 3 (Continuous documentation)
**Depends on:** task spec files (this set). Stands alone otherwise.

## Goal

Keep documentation in lockstep with code so the two never drift. Documentation is
regenerated/patched in the **same PR** that changes code, and a nightly sweep
catches anything missed and opens a standalone `bot/docs-update` PR.

## Audiences & Outputs

Generate and maintain docs for every audience, under `docs/`:

| File | Audience | Contents |
|------|----------|----------|
| `docs/README.md` (or root `README.md`) | Everyone | What the project is, quickstart, links to the rest |
| `docs/architecture.md` | Engineers | System diagram, modules, data flow |
| `docs/api.md` | Integrators | Public functions/endpoints, params, return shapes |
| `docs/operations.md` | Ops/SRE | Run, deploy, env vars, troubleshooting |
| `docs/contributing.md` | Contributors | Setup, branch/PR rules, how the bot pipeline works |
| `docs/CHANGELOG.md` | Everyone | Notable changes per merged PR |

Auto-generated files carry a top banner:
`<!-- maintained by the docs agent — edits here may be overwritten; edit source instead -->`

## Stack Auto-Detection (drives doc tooling)

- Node/TS (`package.json`) → TypeDoc / JSDoc for `docs/api.md`
- Python (`requirements.txt`/`pyproject.toml`) → docstring extraction (pdoc) for `docs/api.md`
- Java (`pom.xml`/`build.gradle`) → Javadoc
- Go (`go.mod`) → `go doc`
- Containerized (`Dockerfile`) → document image, ports, env in `docs/operations.md`

When no recognized source stack is present (e.g. a notes-only repo like the
seed `Rajiv.txt`), generate `docs/architecture.md` from the notes and skip the
api/codegen steps — report "no source stack detected" rather than failing.

## Behaviour

### Per-PR mode (in `docs-continuous.yml`, on `pull_request`)
1. Diff the PR against the base branch; list changed source files.
2. For each changed module, regenerate the affected doc section(s).
3. Commit doc changes onto the **same PR branch** (never a new branch).
4. If nothing changed, do nothing (no empty commits).

### Nightly sweep (on `schedule`)
1. Full regeneration pass across the repo.
2. If the working tree differs from committed docs, open/refresh a
   `bot/docs-update` PR with the delta.
3. If clean, exit 0 with a log line; open no PR.

## Acceptance Criteria

- [ ] `docs/` contains every file in the table above (or a documented reason it's absent).
- [ ] Each auto-generated file has the maintenance banner.
- [ ] Per-PR doc updates land on the PR branch, not a new branch.
- [ ] Nightly sweep opens `bot/docs-update` only when there is a real delta.
- [ ] No AI/assistant attribution anywhere in generated docs.
- [ ] A repo with no source stack produces `architecture.md` and logs the skip — does not error.

## Safety

- Never delete a doc file without explicit confirmation; if a doc's source is
  gone, replace its body with a `> Deprecated:` note instead of deleting.
- Generated YAML/config validated with `actionlint` + dry-run before commit.
