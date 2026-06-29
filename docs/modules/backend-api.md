# Backend API Module

Owner files:

- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/app/storage.py`
- `backend/app/exporter.py`

## Responsibilities

- Initialize SQLite on startup.
- Serve committed frontend assets from `frontend/dist`.
- Provide rule CRUD APIs.
- Run reconciliation for one rule or multiple rules.
- Manage in-memory background batch jobs with progress and cancellation.
- Store and expose reconcile run history.
- Export Excel files for one run or selected runs.

## Current API Surface

- `GET /api/health`
- `GET /`
- `GET /api/rules`
- `POST /api/rules`
- `PUT /api/rules/{rule_id}`
- `DELETE /api/rules/{rule_id}`
- `POST /api/reconcile/run`
- `POST /api/reconcile/batch-run`
- `POST /api/reconcile/batch-run/jobs`
- `GET /api/reconcile/batch-run/jobs/{job_id}`
- `POST /api/reconcile/batch-run/jobs/{job_id}/cancel`
- `GET /api/reconcile/runs`
- `GET /api/reconcile/runs/{run_id}`
- `DELETE /api/reconcile/runs/{run_id}`
- `GET /api/reconcile/runs/{run_id}/export`
- `POST /api/reconcile/runs/compare/export`

## Batch Job Behavior

Background jobs are held in `_batch_jobs`, protected by `_batch_jobs_lock`, and
executed by a `ThreadPoolExecutor(max_workers=2)`.

Statuses:

- `queued`
- `running`
- `cancel_requested`
- `cancelled`
- `completed`

Important limitation: job metadata is process memory only. Reconcile run records
created during the job are persisted, but job progress is lost if the backend
process restarts.

## Failure Behavior

- Single run failures create a failed run record and return HTTP 500 with the
  serialized failed run in `detail.run`.
- Batch failures are collected per rule as `BatchRunFailure`.
- Missing rules are reported as failed batch items.
- Export requests fail with 404 if any requested run is missing.
- Warehouse progress advances by calendar-month query windows, so long
  warehouse runs show month-level progress instead of one coarse source step.

## Change Checklist

- Keep schema changes backward-compatible or document migration.
- Update `frontend/src/api.js` and `frontend-ui.md` if an endpoint contract
  changes.
- Add targeted tests under `backend/tests/`.
- Update `docs/CODEX_CHANGELOG.md` and `docs/open-issues.md`.
