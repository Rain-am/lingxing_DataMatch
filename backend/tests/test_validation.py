import pytest
from fastapi import HTTPException

from app.schemas import Metric, RuleCreate
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
