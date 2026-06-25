from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Optional

from app.schemas import Granularity, ReconcileRow, ReconcileStatus, ReconcileSummaryRow, Rule, Source


ProgressCallback = Callable[..., None]


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


def _metric_tolerance(rule: Rule, metric_name: str) -> Decimal:
    for source in rule.sources:
        for metric in source.metrics:
            if metric.name == metric_name:
                return metric.tolerance
    for metric in rule.metrics:
        if metric.name == metric_name:
            return metric.tolerance
    return Decimal("0")


def _base_source(rule: Rule) -> str:
    if rule.comparison_base_source:
        return rule.comparison_base_source
    for source in rule.sources:
        if source.type == "warehouse":
            return source.name
    return rule.sources[0].name if rule.sources else "数仓"


def _legacy_sources(rule: Rule) -> list[Source]:
    if rule.sources:
        return rule.sources
    return [
        Source(
            name="数仓",
            type="warehouse",
            table_or_path=rule.warehouse_table,
            date_field=rule.warehouse_date_field,
            store_field=rule.warehouse_store_field,
            metrics=rule.metrics,
        ),
        Source(
            name="ERP",
            type="erp",
            table_or_path=rule.erp_module_path,
            date_field=rule.erp_date_field,
            store_field=rule.erp_store_field,
            request_config=rule.erp_request_config,
            metrics=rule.metrics,
        ),
    ]


def collect_source_values(
    rule: Rule,
    start_date: str,
    end_date: str,
    granularity: Granularity,
    progress_callback: Optional[ProgressCallback] = None,
) -> dict[tuple[str, str, str, str], Decimal]:
    values: dict[tuple[str, str, str, str], Decimal] = {}
    for source in _legacy_sources(rule):
        if source.type == "warehouse":
            from app.warehouse import fetch_warehouse_source_values

            source_values = fetch_warehouse_source_values(source, start_date, end_date, granularity, progress_callback)
        else:
            from app.lianxing_api import fetch_erp_source_values

            source_values = fetch_erp_source_values(source, start_date, end_date, granularity, progress_callback=progress_callback)
        values.update(source_values)
    return values


def build_multisource_rows(
    rule: Rule,
    values: dict[tuple[str, str, str, str], Decimal],
) -> list[ReconcileRow]:
    sources = _legacy_sources(rule)
    source_names = [source.name for source in sources]
    base_source = _base_source(rule)
    metric_names = {metric.name for source in sources for metric in source.metrics}
    dimensions = sorted({(period, store, metric) for period, store, metric, _source in values})
    rows: list[ReconcileRow] = []
    for period, store, metric_name in dimensions:
        source_values = {
            source: values.get((period, store, metric_name, source), Decimal("0")) for source in source_names
        }
        base_value = source_values.get(base_source, Decimal("0"))
        tolerance = _metric_tolerance(rule, metric_name)
        for source in source_names:
            value = source_values[source]
            diff = base_value - value
            rows.append(
                ReconcileRow(
                    period=period,
                    store=store,
                    metric=metric_name,
                    source=source,
                    value=value,
                    warehouse_value=base_value,
                    erp_value=value,
                    diff_value=diff,
                    diff_rate=_rate(diff, value),
                    tolerance=tolerance,
                    status=_status(abs(diff), tolerance),
                )
            )
    if not metric_names:
        return rows
    return rows


def build_summary_rows(rule: Rule, rows: list[ReconcileRow]) -> list[ReconcileSummaryRow]:
    base_source = _base_source(rule)
    groups: dict[tuple[str, str], dict[str, Decimal]] = {}
    for row in rows:
        key = (row.period, row.metric)
        groups.setdefault(key, {})
        groups[key][row.source] = groups[key].get(row.source, Decimal("0")) + row.value

    summary: list[ReconcileSummaryRow] = []
    for (period, metric), values in sorted(groups.items()):
        base_value = values.get(base_source, Decimal("0"))
        tolerance = _metric_tolerance(rule, metric)
        diffs = {source: base_value - value for source, value in values.items() if source != base_source}
        worst = "matched"
        for diff in diffs.values():
            status = _status(abs(diff), tolerance)
            if status == "major_diff":
                worst = "major_diff"
                break
            if status == "minor_diff":
                worst = "minor_diff"
        summary.append(ReconcileSummaryRow(period=period, metric=metric, values=values, diffs=diffs, status=worst))
    return summary


def build_reconcile_rows(
    rule: Rule,
    start_date: str,
    end_date: str,
    granularity: Granularity,
    warehouse_values: Optional[dict[tuple[str, str, str], Decimal]] = None,
    erp_values: Optional[dict[tuple[str, str, str], Decimal]] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> list[ReconcileRow]:
    if rule.sources and warehouse_values is None and erp_values is None:
        values = collect_source_values(rule, start_date, end_date, granularity, progress_callback)
        return build_multisource_rows(rule, values)

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
                source="ERP",
                value=erp_value,
                warehouse_value=warehouse_value,
                erp_value=erp_value,
                diff_value=diff_value,
                diff_rate=_rate(diff_value, erp_value),
                tolerance=metric.tolerance,
                status=_status(diff_abs, metric.tolerance),
            )
        )
    return rows


def build_reconcile_result(
    rule: Rule,
    start_date: str,
    end_date: str,
    granularity: Granularity,
    progress_callback: Optional[ProgressCallback] = None,
) -> tuple[list[ReconcileRow], list[ReconcileSummaryRow]]:
    rows = build_reconcile_rows(rule, start_date, end_date, granularity, progress_callback=progress_callback)
    if progress_callback:
        progress_callback(stage="聚合结果", detail="生成汇总结果", advance=1)
    return rows, build_summary_rows(rule, rows)
