# Storage And Schema Module

Owner files:

- `backend/app/storage.py`
- `backend/app/schemas.py`

## SQLite Tables

### `rules`

Current columns:

- `id`
- `name`
- `warehouse_table`
- `warehouse_date_field`
- `warehouse_store_field`
- `erp_module_path`
- `erp_date_field`
- `erp_store_field`
- `erp_request_config_json`
- `metrics_json`
- `sources_json`
- `comparison_base_source`
- `created_at`
- `updated_at`

Legacy columns remain populated for compatibility even when `sources_json` is
the primary structured representation.

### `reconcile_runs`

Current columns:

- `id`
- `rule_id`
- `rule_name`
- `start_date`
- `end_date`
- `granularity`
- `status`
- `rows_json`
- `summary_rows_json`
- `error_message`
- `created_at`

## Additive Migrations

`init_db()` creates both tables if missing and adds these columns when absent:

- `rules.erp_request_config_json`
- `rules.sources_json`
- `rules.comparison_base_source`
- `reconcile_runs.summary_rows_json`

No destructive migration framework exists yet.

## Pydantic Models

Important models in `schemas.py`:

- `Metric`
- `StoreMapping`
- `Source`
- `RuleCreate`, `RuleUpdate`, `Rule`
- `RunRequest`, `BatchRunRequest`
- `ReconcileRow`, `ReconcileSummaryRow`, `ReconcileRun`
- `BatchRunJob`, `BatchRunFailure`, `BatchRunResponse`

## Change Checklist

- Prefer additive migrations.
- Preserve old stored rules unless a migration plan and backup path are written.
- Add tests for defaulting, serialization, and backward compatibility.
- Coordinate frontend payload changes with `frontend-ui.md`.

