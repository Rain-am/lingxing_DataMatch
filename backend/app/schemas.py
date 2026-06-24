from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, validator


Aggregation = Literal["sum", "count"]
Granularity = Literal["day", "month"]
ReconcileStatus = Literal["matched", "minor_diff", "major_diff"]


class Metric(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    warehouse_expression: str = Field(min_length=1, max_length=300)
    erp_field: str = Field(min_length=1, max_length=120)
    aggregation: Aggregation = "sum"
    tolerance: Decimal = Decimal("0")

    @validator("tolerance")
    def tolerance_must_be_positive(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("tolerance must be greater than or equal to 0")
        return value


class RuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    warehouse_table: str = Field(min_length=1, max_length=120)
    warehouse_date_field: str = Field(min_length=1, max_length=120)
    warehouse_store_field: str = Field(min_length=1, max_length=120)
    erp_module_path: str = Field(min_length=1, max_length=300)
    erp_date_field: str = Field(min_length=1, max_length=120)
    erp_store_field: str = Field(min_length=1, max_length=120)
    erp_request_config: dict[str, Any] = Field(default_factory=dict)
    metrics: list[Metric] = Field(min_length=1)


class RuleCreate(RuleBase):
    pass


class RuleUpdate(RuleBase):
    pass


class Rule(RuleBase):
    id: int
    created_at: datetime
    updated_at: datetime


class RunRequest(BaseModel):
    rule_id: int
    start_date: date
    end_date: date
    granularity: Granularity = "day"

    @validator("end_date")
    def end_must_not_precede_start(cls, value: date, values: Any) -> date:
        start_date = values.get("start_date")
        if start_date and value < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return value


class ReconcileRow(BaseModel):
    period: str
    store: str
    metric: str
    warehouse_value: Decimal
    erp_value: Decimal
    diff_value: Decimal
    diff_rate: Optional[Decimal]
    tolerance: Decimal
    status: ReconcileStatus


class ReconcileRun(BaseModel):
    id: int
    rule_id: int
    rule_name: str
    start_date: date
    end_date: date
    granularity: Granularity
    status: str
    rows: list[ReconcileRow]
    error_message: Optional[str] = None
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    app: str
