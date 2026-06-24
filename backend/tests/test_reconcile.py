from datetime import datetime
from decimal import Decimal

from app.lianxing_api import _month_windows
from app.reconcile import build_multisource_rows, build_reconcile_rows, build_summary_rows
from app.schemas import Metric, Rule, Source


def _legacy_rule() -> Rule:
    return Rule(
        id=1,
        name="销售核对",
        warehouse_table="orders",
        warehouse_date_field="biz_date",
        warehouse_store_field="store_name",
        erp_module_path="/orders/list",
        erp_date_field="biz_date",
        erp_store_field="store_name",
        metrics=[
            Metric(name="销售额", warehouse_expression="amount", erp_field="amount", aggregation="sum", tolerance=Decimal("1")),
            Metric(name="订单数", warehouse_expression="*", erp_field="order_id", aggregation="count", tolerance=Decimal("0")),
        ],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _multi_rule() -> Rule:
    return Rule(
        id=2,
        name="多来源利润核对",
        comparison_base_source="数仓利润表",
        sources=[
            Source(
                name="数仓利润表",
                type="warehouse",
                table_or_path="bi_profit_report",
                date_field="dataDate",
                store_field="storeName",
                metrics=[Metric(name="毛利润", warehouse_expression="grossProfit", erp_field="grossProfit")],
            ),
            Source(
                name="ERP订单利润",
                type="erp",
                table_or_path="/basicOpen/finance/mreport/OrderProfit",
                date_field="",
                store_field="storeName",
                period_mode="request_month",
                request_config={"extraParams": {"currencyCode": "USD"}},
                metrics=[Metric(name="毛利润", warehouse_expression="grossProfit", erp_field="grossProfit")],
            ),
        ],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def test_build_reconcile_rows_statuses() -> None:
    rule = _legacy_rule()
    warehouse = {
        ("2026-01-01", "A店", "销售额"): Decimal("100"),
        ("2026-01-01", "A店", "订单数"): Decimal("3"),
    }
    erp = {
        ("2026-01-01", "A店", "销售额"): Decimal("99.5"),
        ("2026-01-01", "A店", "订单数"): Decimal("2"),
    }
    rows = build_reconcile_rows(rule, "2026-01-01", "2026-01-31", "day", warehouse, erp)

    amount = next(row for row in rows if row.metric == "销售额")
    count = next(row for row in rows if row.metric == "订单数")
    assert amount.status == "minor_diff"
    assert amount.diff_value == Decimal("0.5")
    assert count.status == "major_diff"
    assert count.diff_value == Decimal("1")


def test_build_reconcile_rows_handles_missing_side() -> None:
    rule = _legacy_rule()
    rows = build_reconcile_rows(
        rule,
        "2026-01-01",
        "2026-01-31",
        "month",
        {("2026-01-01", "A店", "销售额"): Decimal("10")},
        {},
    )

    assert rows[0].erp_value == Decimal("0")
    assert rows[0].warehouse_value == Decimal("10")
    assert rows[0].diff_rate is None


def test_multisource_summary_uses_base_source() -> None:
    rule = _multi_rule()
    values = {
        ("2026-04-01", "A店", "毛利润", "数仓利润表"): Decimal("100"),
        ("2026-04-01", "A店", "毛利润", "ERP订单利润"): Decimal("95"),
        ("2026-04-01", "B店", "毛利润", "数仓利润表"): Decimal("60"),
        ("2026-04-01", "B店", "毛利润", "ERP订单利润"): Decimal("70"),
    }

    rows = build_multisource_rows(rule, values)
    summary = build_summary_rows(rule, rows)

    assert len(summary) == 1
    assert summary[0].values["数仓利润表"] == Decimal("160")
    assert summary[0].values["ERP订单利润"] == Decimal("165")
    assert summary[0].diffs["ERP订单利润"] == Decimal("-5")
    assert summary[0].status == "major_diff"


def test_request_month_windows_clip_date_range() -> None:
    assert _month_windows("2026-01-15", "2026-03-05") == [
        ("2026-01-01", "2026-01-15", "2026-01-31"),
        ("2026-02-01", "2026-02-01", "2026-02-28"),
        ("2026-03-01", "2026-03-01", "2026-03-05"),
    ]
