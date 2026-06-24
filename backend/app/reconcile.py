from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.schemas import Granularity, ReconcileRow, ReconcileStatus, Rule


def _rate(diff: Decimal, erp_value: Decimal) -> Optional[Decimal]:
    if erp_value == 0:
        return None
    return (diff / erp_value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _status(diff_abs: Decimal, tolerance: Decimal) -> ReconcileStatus:
    if diff_abs == 0:
        return "matched"
    if diff_abs <= tolerance:
        return "minor_diff"
    return "major_diff"


def build_reconcile_rows(
    rule: Rule,
    start_date: str,
    end_date: str,
    granularity: Granularity,
    warehouse_values: Optional[dict[tuple[str, str, str], Decimal]] = None,
    erp_values: Optional[dict[tuple[str, str, str], Decimal]] = None,
) -> list[ReconcileRow]:
    warehouse = warehouse_values
    if warehouse is None:
        from app.warehouse import fetch_warehouse_aggregate

        warehouse = fetch_warehouse_aggregate(rule, start_date, end_date, granularity)
    erp = erp_values
    if erp is None:
        from app.lianxing_api import fetch_erp_aggregate

        erp = fetch_erp_aggregate(rule, start_date, end_date, granularity)

    metric_by_name = {metric.name: metric for metric in rule.metrics}
    keys = sorted(set(warehouse.keys()) | set(erp.keys()))
    rows: list[ReconcileRow] = []
    for period, store, metric_name in keys:
        metric = metric_by_name[metric_name]
        warehouse_value = warehouse.get((period, store, metric_name), Decimal("0"))
        erp_value = erp.get((period, store, metric_name), Decimal("0"))
        diff_value = warehouse_value - erp_value
        diff_abs = abs(diff_value)
        rows.append(
            ReconcileRow(
                period=period,
                store=store,
                metric=metric_name,
                warehouse_value=warehouse_value,
                erp_value=erp_value,
                diff_value=diff_value,
                diff_rate=_rate(diff_value, erp_value),
                tolerance=metric.tolerance,
                status=_status(diff_abs, metric.tolerance),
            )
        )
    return rows
