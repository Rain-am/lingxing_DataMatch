# Codex Changelog

This file records repository-level changes made or reconstructed by Codex. Keep
the newest entries at the top. When reading project state, review the latest 10
entries plus `docs/open-issues.md`.

Before 2026-06-26 this repository did not contain a Codex changelog, so the
baseline entries below summarize the current code shape from repository files
rather than a historical commit-by-commit record.

## 2026-06-29 - Stabilized warehouse month-range queries

- Split warehouse aggregate queries into calendar-month windows so long date
  ranges no longer rely on one large MySQL query over the SSH tunnel.
- Added configurable MySQL connect/read/write timeouts and a one-time retry for
  transient MySQL disconnects.
- Updated background job progress sizing so warehouse sources advance by month.
- Verification: `python -m pytest backend\tests` passed with 31 tests.

## 2026-06-26 - Optimized run reconciliation controls

- Added quick date ranges for current month, previous month, recent three
  natural months, and custom dates on the run reconciliation page.
- Defaulted empty run-date fields to the current full month when entering the
  run page.
- Moved the running-job cancel button next to the selected-rule count above the
  rule checklist.
- Rebuilt committed frontend assets in `frontend/dist`.
- Verification: `npm.cmd run build` succeeded; `pnpm build` was unavailable in
  this environment.

## 2026-06-26 - Added project control documentation framework

- Added root `AGENTS.md` with startup checklist, module ownership, handoff
  format, and documentation rules.
- Added root `PROJECT_CONTEXT.md` with current objective, architecture, module
  status, assumptions, and known gaps.
- Added `docs/open-issues.md` and `docs/modules/` module facts.
- Updated README navigation to point future contributors at these docs.
- Verification: docs/file inspection and git diff only; no build or tests run.

## 2026-06-26 - Baseline: backend API surface

- Current backend exposes health, frontend index, rule CRUD, single reconcile
  run, synchronous batch run, background batch job create/get/cancel, run
  history list/get/delete, single-run export, and selected-run compare export.
- Owner: `backend/app/main.py`.
- Verification: reconstructed from source inspection.

## 2026-06-26 - Baseline: reconciliation engine

- Current reconciliation logic supports legacy two-source rules and newer
  multi-source rules.
- It calculates source values, base-source differences, diff rates, tolerance
  statuses, and period/metric summary rows.
- Owner: `backend/app/reconcile.py`.
- Verification: reconstructed from source inspection.

## 2026-06-26 - Baseline: warehouse adapter

- Current warehouse adapter queries MySQL directly or through an SSH tunnel,
  aggregates by date/month and store, supports sum/count metrics, and applies
  optional store mapping.
- Owner: `backend/app/warehouse.py`.
- Verification: reconstructed from source inspection.

## 2026-06-26 - Baseline: Lingxing OpenAPI adapter

- Current Lingxing adapter manages access token refresh, AES signing, JSON POST
  requests, retry on transient URL errors, auth-error retry after refresh,
  pagination, order-profit offset defaults, nested fields, and request-month
  windows.
- Owner: `backend/app/lianxing_api.py`.
- Verification: reconstructed from source inspection.

## 2026-06-26 - Baseline: persistence and compatibility

- Current SQLite storage keeps rule legacy columns plus JSON `sources`,
  `comparison_base_source`, run rows, and summary rows.
- Startup performs additive migrations for missing JSON/summary columns.
- Owners: `backend/app/storage.py`, `backend/app/schemas.py`.
- Verification: reconstructed from source inspection.

## 2026-06-26 - Baseline: frontend workflow

- Current Vue UI has rule management, run selection, background batch progress,
  cancellation, failed-run display, result history, run deletion, selected-run
  comparison, filters, store-level drilldown, and compare export.
- Owners: `frontend/src/App.vue`, `frontend/src/api.js`.
- Verification: reconstructed from source inspection.

## 2026-06-26 - Baseline: Excel export

- Current export module creates single-run workbooks with summary, store detail,
  and parameters sheets, plus selected-run comparison workbooks with summary,
  detail, and run metadata sheets.
- Owner: `backend/app/exporter.py`.
- Verification: reconstructed from source inspection.

## 2026-06-26 - Baseline: deployment model

- Current deployment docs recommend isolated Linux install under
  `/opt/lingxing-reconcile`, systemd service `lingxing-reconcile.service`, and
  local-only listen address `127.0.0.1:18081`.
- Windows local entrypoints include a root `.bat` and PowerShell helper scripts.
- Owners: `deploy/`, `scripts/`, root `.bat`.
- Verification: reconstructed from source inspection.

## 2026-06-26 - Baseline: test coverage map

- Current backend tests cover validation, storage ordering, run deletion APIs,
  batch job behavior, reconciliation statuses and summaries, Lingxing API
  signing/token/pagination behavior, nested fields, and store mapping.
- Owner: `backend/tests/`.
- Verification: test files inspected; tests not run in this documentation pass.
