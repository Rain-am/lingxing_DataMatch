# Project Context

Last reviewed: 2026-06-26

## Current Objective

Lingxing Data Match is a reconciliation application for comparing Lingxing data
warehouse MySQL aggregates with Lingxing ERP OpenAPI data. It is intended to run
locally on Windows and as an isolated Linux service.

The current product shape is:

- Users create reconciliation rules.
- A rule defines warehouse source fields, ERP source fields, metrics, tolerance,
  request configuration, and optional store mapping.
- Users run one or more rules for a date range and day/month granularity.
- The backend fetches source data, aggregates it, calculates differences and
  statuses, stores a run record, and exposes result history.
- The frontend lets users compare selected runs, inspect store-level details,
  delete run records, and export Excel files.

## Highest Priority

Keep a reliable project fact base in the repository. Before this documentation
framework was added, the expected control files were missing. Future agents must
keep `AGENTS.md`, this file, `docs/CODEX_CHANGELOG.md`, `docs/open-issues.md`,
and `docs/modules/` aligned with the code.

## Architecture

```text
browser
  -> FastAPI backend
      -> SQLite: rules and reconcile run history
      -> MySQL: Lingxing data warehouse aggregate queries
      -> Lingxing OpenAPI: ERP source records
      -> openpyxl: Excel exports
```

Frontend:

- Vue 3 + Vite.
- Source lives in `frontend/src/`.
- Production assets are committed in `frontend/dist/` and served by FastAPI when
  present.

Backend:

- FastAPI app entry: `backend/app/main.py`.
- Settings are loaded from environment and `backend/.env`.
- SQLite path defaults to `backend/data/reconcile.db`.
- MySQL can connect directly or through an SSH tunnel.
- Lingxing OpenAPI signing uses `access_token`, `app_key`, `timestamp`, and AES
  encrypted `sign`.

## Current Module Status

- Rule management: implemented through CRUD API and Vue rule editor.
- Reconciliation runs: implemented for single run, immediate batch run, and
  background batch jobs.
- Batch progress and cancellation: implemented in memory. Job state is not
  persisted across backend restarts.
- Multi-source comparison: implemented with `sources` and
  `comparison_base_source`, while legacy rule columns are still retained for
  compatibility.
- Store mapping: implemented for warehouse and ERP sources through a warehouse
  mapping table.
- Result history: implemented in SQLite with list/get/delete APIs.
- Excel export: implemented for single run and selected-run comparison.
- Deployment: documented for Windows local run and Linux systemd service.

## Operational Assumptions

- `backend/.env` is local/server-only and must not be committed.
- First Linux deployment should bind to `127.0.0.1:18081` and be accessed
  through SSH port forwarding.
- The root `.bat` starts the backend and serves committed frontend assets; it
  does not rebuild `frontend/dist`.
- `scripts/start-app.ps1` rebuilds the frontend before starting the backend and
  assumes local runtime paths and frontend dependencies are available.
- Committed `frontend/dist` must be refreshed whenever frontend source changes
  are meant to ship without a separate build step.

## Known Gaps

See `docs/open-issues.md` for the active issue list. The main current gaps are
documentation alignment, committed frontend build freshness, and operational
clarity around the two Windows launch paths.

## Verification Baseline

The repository contains backend pytest coverage for validation, storage, delete
APIs, batch jobs, reconciliation logic, Lingxing API behavior, field extraction,
and store mapping.

No build or test results are implied by this file. Each task must record what it
actually ran.

