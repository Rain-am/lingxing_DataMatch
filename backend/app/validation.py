import re

from fastapi import HTTPException

from app.schemas import RuleBase, Source

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
    sources = payload.sources
    if not sources:
        if payload.warehouse_table:
            validate_identifier(payload.warehouse_table, "warehouse_table")
            validate_identifier(payload.warehouse_date_field, "warehouse_date_field")
            validate_identifier(payload.warehouse_store_field, "warehouse_store_field")
        if payload.erp_module_path:
            validate_module_path(payload.erp_module_path)
        for metric in payload.metrics:
            validate_expression(metric.warehouse_expression, f"metric {metric.name} warehouse_expression")
        return

    if len({source.name for source in sources}) != len(sources):
        raise HTTPException(status_code=400, detail="source names must be unique")
    for source in sources:
        validate_source(source)


def validate_source(source: Source) -> None:
    if source.store_mapping.enabled:
        validate_identifier(source.store_mapping.table, f"source {source.name} store mapping table")
        validate_identifier(source.store_mapping.id_field, f"source {source.name} store mapping id_field")
        validate_identifier(source.store_mapping.name_field, f"source {source.name} store mapping name_field")
    if source.type == "warehouse":
        validate_identifier(source.table_or_path, f"source {source.name} table")
        validate_identifier(source.date_field, f"source {source.name} date_field")
        validate_identifier(source.store_field, f"source {source.name} store_field")
        for metric in source.metrics:
            validate_expression(metric.warehouse_expression, f"source {source.name} metric {metric.name}")
    else:
        validate_module_path(source.table_or_path)
        if source.period_mode == "response_field":
            validate_identifier(source.date_field, f"source {source.name} date_field")
        validate_identifier(source.store_field, f"source {source.name} store_field")
