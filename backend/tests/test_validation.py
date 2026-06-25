import pytest
from fastapi import HTTPException

from app.schemas import Metric, RuleCreate, Source
from app.validation import validate_rule_payload


def test_validate_rule_rejects_bad_table_name() -> None:
    payload = RuleCreate(
        name="bad",
        warehouse_table="orders;drop",
        warehouse_date_field="biz_date",
        warehouse_store_field="store_name",
        erp_module_path="/orders/list",
        erp_date_field="biz_date",
        erp_store_field="store_name",
        metrics=[Metric(name="销售额", warehouse_expression="amount", erp_field="amount")],
    )
    with pytest.raises(HTTPException):
        validate_rule_payload(payload)


def test_validate_rule_accepts_simple_expression() -> None:
    payload = RuleCreate(
        name="ok",
        warehouse_table="orders",
        warehouse_date_field="biz_date",
        warehouse_store_field="store_name",
        erp_module_path="/orders/list",
        erp_date_field="biz_date",
        erp_store_field="store_name",
        metrics=[Metric(name="销售额", warehouse_expression="amount + tax", erp_field="amount")],
    )
    validate_rule_payload(payload)


def test_validate_rule_accepts_erp_field_paths() -> None:
    payload = RuleCreate(
        name="ok",
        sources=[
            Source(
                name="ERP",
                type="erp",
                table_or_path="/basicOpen/finance/mreport/OrderProfit",
                date_field="",
                store_field="data>>sids",
                period_mode="request_month",
                metrics=[Metric(name="毛利润", warehouse_expression="gross_profit", erp_field="data>>gross_profit")],
            )
        ],
    )

    validate_rule_payload(payload)


def test_validate_rule_rejects_bad_erp_field_path() -> None:
    payload = RuleCreate(
        name="bad",
        sources=[
            Source(
                name="ERP",
                type="erp",
                table_or_path="/basicOpen/finance/mreport/OrderProfit",
                date_field="",
                store_field="data>>sids;drop",
                period_mode="request_month",
                metrics=[Metric(name="毛利润", warehouse_expression="gross_profit", erp_field="data>>gross_profit")],
            )
        ],
    )

    with pytest.raises(HTTPException):
        validate_rule_payload(payload)
