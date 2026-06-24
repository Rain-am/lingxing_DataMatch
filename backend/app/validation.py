import re

from fastapi import HTTPException

from app.schemas import RuleBase

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MODULE_PATH_RE = re.compile(r"^/?[A-Za-z0-9_./-]+$")
EXPRESSION_RE = re.compile(r"^[A-Za-z0-9_`().,+\-*/\s]+$")


def validate_identifier(value: str, label: str) -> None:
    if not IDENTIFIER_RE.match(value):
        raise HTTPException(status_code=400, detail=f"{label} must be a simple SQL identifier")


def validate_expression(value: str, label: str) -> None:
    if ";" in value or "--" in value or "/*" in value or "*/" in value:
        raise HTTPException(status_code=400, detail=f"{label} contains forbidden SQL tokens")
    if not EXPRESSION_RE.match(value):
        raise HTTPException(status_code=400, detail=f"{label} contains unsupported characters")


def validate_module_path(value: str) -> None:
    if not MODULE_PATH_RE.match(value):
        raise HTTPException(status_code=400, detail="ERP module path contains unsupported characters")


def validate_rule_payload(payload: RuleBase) -> None:
    validate_identifier(payload.warehouse_table, "warehouse_table")
    validate_identifier(payload.warehouse_date_field, "warehouse_date_field")
    validate_identifier(payload.warehouse_store_field, "warehouse_store_field")
    validate_module_path(payload.erp_module_path)
    for metric in payload.metrics:
        validate_expression(metric.warehouse_expression, f"metric {metric.name} warehouse_expression")
