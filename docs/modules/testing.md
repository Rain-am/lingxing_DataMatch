# Testing Module

Owner directory:

- `backend/tests/`

## Current Test Map

- `test_validation.py`: rule validation and field/expression validation.
- `test_store_mapping.py`: store mapping query behavior.
- `test_storage_runs.py`: run history ordering.
- `test_run_delete_api.py`: run delete API 404 behavior.
- `test_delete_runs.py`: deleting one run without deleting others.
- `test_reconcile.py`: statuses, missing sides, multisource summary,
  request-month windows.
- `test_lianxing_fields.py`: nested ERP field extraction and nested data arrays.
- `test_lianxing_api.py`: HTTP error redaction, token generation/refresh, auth
  retry, forced USD, order-profit pagination, secret exposure checks.
- `test_batch_jobs_api.py`: batch job completion and cancellation behavior.
- `test_warehouse.py`: warehouse date-window helper behavior.

## Verification Guidelines

- Docs-only changes: no test run required; inspect diff.
- Schema/storage changes: run storage and API tests.
- Reconciliation logic changes: run `test_reconcile.py` plus affected source
  adapter tests.
- Lingxing API changes: run `test_lianxing_api.py` and
  `test_lianxing_fields.py`.
- Frontend changes: run frontend build if allowed and update committed dist if
  shipping the UI.

## Notes

No current CI configuration is documented in this repository. Each final handoff
must say which tests/builds were actually run and which were skipped.
