# Reconciliation Core Module

Owner file:

- `backend/app/reconcile.py`

## Responsibilities

- Fetch source aggregates through data-source adapters.
- Support legacy two-source rules and newer multi-source `sources` rules.
- Compare each source against a configured base source.
- Calculate difference, difference rate, tolerance status, and summary rows.

## Key Concepts

Rule:

- Legacy fields: `warehouse_table`, `warehouse_date_field`,
  `warehouse_store_field`, `erp_module_path`, `erp_date_field`,
  `erp_store_field`, `metrics`.
- New fields: `sources`, `comparison_base_source`.

Source:

- `name`
- `type`: `warehouse` or `erp`
- `table_or_path`
- `date_field`
- `store_field`
- `period_mode`: `response_field` or `request_month`
- `request_config`
- `metrics`
- `store_mapping`

Metric:

- `name`
- `warehouse_expression`
- `erp_field`
- `aggregation`: `sum` or `count`
- `tolerance`

## Status Semantics

- `matched`: absolute diff is zero.
- `minor_diff`: absolute diff is greater than zero and less than or equal to
  tolerance.
- `major_diff`: absolute diff is greater than tolerance.

Difference rate is `diff / compared_value`, rounded to four decimal places. If
the compared value is zero, the rate is `null`.

## Summary Behavior

Detailed rows are grouped by `(period, store, metric, source)`. Summary rows are
grouped by `(period, metric)` and include:

- `values`: source totals for the group.
- `diffs`: base-source total minus each non-base source total.
- `status`: worst status among source diffs for the metric/period.

## Compatibility Notes

If a rule has no `sources`, the core builds a legacy pair:

- `数仓`
- `ERP`

Frontend code still includes fallback support for mojibake legacy source names
that may appear in older stored data.

## Change Checklist

- Any math/status change needs tests in `backend/tests/test_reconcile.py`.
- Any output-shape change needs updates to frontend result comparison and Excel
  export docs.
- Any source semantics change needs updates to `data-sources.md`.

