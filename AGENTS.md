# Agent Operating Guide

This file is the first stop for any Codex or assistant window working on this
repository. Treat repository files and git state as the source of truth; do not
rely on chat memory when taking over work.

## Required Startup Checklist

Before planning or editing, read:

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. The latest 10 entries in `docs/CODEX_CHANGELOG.md`
4. `docs/modules/README.md` and any module file relevant to the request
5. `docs/open-issues.md`
6. `git status --short --branch`
7. `git diff --stat`

If any listed file is missing, recreate it or explicitly report the gap before
starting product work.

## Project Mission

Build and maintain a local/server-deployable reconciliation tool that compares
Lingxing data warehouse MySQL aggregates with Lingxing ERP OpenAPI data. The
tool stores rules in SQLite, runs single or batch reconciliations, records
results, and exports Excel reports.

## Operating Principles

- Keep business behavior and project governance separate. Documentation-only
  changes should not modify runtime code.
- Keep secrets out of git. Never commit `backend/.env`, credentials, tokens, or
  downloaded production data.
- Prefer narrow changes. Touch the module that owns the behavior and update its
  module doc when the behavior changes.
- Preserve existing compatibility fields unless a migration plan is documented.
- Use UTF-8 for project files. The UI and docs contain Chinese text by design.
- Do not run build, tests, network calls, or live data probes when the user has
  asked for read-only or docs-only work.

## Module Ownership

Use `docs/modules/README.md` as the module index. The main boundaries are:

- Backend API and job orchestration: `backend/app/main.py`
- Reconciliation logic: `backend/app/reconcile.py`
- Data source adapters: `backend/app/warehouse.py`, `backend/app/lianxing_api.py`
- Persistence and schemas: `backend/app/storage.py`, `backend/app/schemas.py`
- Validation: `backend/app/validation.py`
- Excel export: `backend/app/exporter.py`
- Frontend: `frontend/src/`
- Deployment and scripts: `deploy/`, `scripts/`, root `.bat`

## Documentation Rules

When changing product behavior, update all relevant facts:

- Add a concise entry to `docs/CODEX_CHANGELOG.md`.
- Update the owning file under `docs/modules/`.
- Add or close items in `docs/open-issues.md`.
- Update `PROJECT_CONTEXT.md` when the project goal, priorities, architecture, or
  operational assumptions change.
- Update README only for user-facing getting-started or navigation changes.

## Task Handoff Format

For a new feature conversation, start with:

```text
Project: Lingxing Data Match
Goal:
Module(s):
Relevant docs:
Acceptance criteria:
Constraints:
Do not:
```

Recommended module-specific task splits:

- API/backend task: endpoint contract, schema change, storage impact, tests.
- Reconciliation task: input rows, aggregation, tolerance/status semantics, tests.
- Data-source task: MySQL query, Lingxing request/signing/pagination, real-data
  assumptions, mocked tests.
- Frontend task: user workflow, API payloads, empty/loading/error states,
  responsive layout, build/dist impact.
- Deployment task: Windows launch, Linux service, env variables, rollback.
- Documentation task: facts only, no runtime changes unless requested.

## Verification Expectations

Choose verification based on change risk:

- Docs-only: inspect files and `git diff --stat`.
- Python logic/API: run targeted pytest files if allowed.
- Frontend source: run build if allowed, and remember that committed `dist` can
  diverge from `src`.
- Deployment scripts: inspect command paths and ports; do not stop running
  services unless the user explicitly asks.

Record skipped verification in the final response.

