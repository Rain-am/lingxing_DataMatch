# Export And Reporting Module

Owner file:

- `backend/app/exporter.py`

## Single Run Export

Endpoint:

- `GET /api/reconcile/runs/{run_id}/export`

Workbook sheets:

- `横向汇总`
- `店铺明细`
- `运行参数`

Rows are filled with status colors:

- `matched`: green
- `minor_diff`: yellow
- `major_diff`: red
- `failed`: red

## Selected Run Compare Export

Endpoint:

- `POST /api/reconcile/runs/compare/export`

Workbook sheets:

- `所选结果对比`
- `店铺明细`
- `运行结果`

## Current Limitations

- Export files use generated filenames only.
- Compare summary currently sums all source values for a run label rather than
  exposing source-specific columns.
- Formatting is intentionally simple: bold headers, autosized columns, status
  fill colors.

## Change Checklist

- If row or summary schemas change, update export columns.
- Add tests when report shape becomes contractual.
- Keep worksheet names short enough for Excel compatibility.

