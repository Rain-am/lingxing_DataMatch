from datetime import datetime
from decimal import Decimal

from app.reconcile import build_reconcile_rows
from app.schemas import Metric, Rule


def _rule() -> Rule:
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
            Metric(
                name="销售额",
                warehouse_expression="amount",
                erp_field="amount",
                aggregation="sum",
                tolerance=Decimal("1"),
            ),
            Metric(
                name="订单数",
                warehouse_expression="*",
                erp_field="order_id",
                aggregation="count",
                tolerance=Decimal("0"),
            ),
        ],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def test_build_reconcile_rows_statuses() -> None:
    rule = _rule()
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
    rule = _rule()
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
