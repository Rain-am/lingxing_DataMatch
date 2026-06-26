from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, validator


Aggregation = Literal["sum", "count"]
Granularity = Literal["day", "month"]
ReconcileStatus = Literal["matched", "minor_diff", "major_diff"]
SourceType = Literal["warehouse", "erp"]
PeriodMode = Literal["response_field", "request_month"]


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


class StoreMapping(BaseModel):
    enabled: bool = False
    table: str = "seller"
    id_field: str = "sid"
    name_field: str = "name"


class Source(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: SourceType
    table_or_path: str = Field(min_length=1, max_length=300)
    date_field: str = Field(default="", max_length=120)
    store_field: str = Field(min_length=1, max_length=120)
    period_mode: PeriodMode = "response_field"
    request_config: dict[str, Any] = Field(default_factory=dict)
    metrics: list[Metric] = Field(min_items=1)
    store_mapping: StoreMapping = Field(default_factory=StoreMapping)


class RuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    warehouse_table: str = ""
    warehouse_date_field: str = ""
    warehouse_store_field: str = ""
    erp_module_path: str = ""
    erp_date_field: str = ""
    erp_store_field: str = ""
    erp_request_config: dict[str, Any] = Field(default_factory=dict)
    metrics: list[Metric] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    comparison_base_source: str = ""


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


class BatchRunRequest(BaseModel):
    rule_ids: list[int] = Field(min_items=1)
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
    source: str = ""
    value: Decimal = Decimal("0")
    warehouse_value: Decimal = Decimal("0")
    erp_value: Decimal = Decimal("0")
    diff_value: Decimal = Decimal("0")
    diff_rate: Optional[Decimal] = None
    tolerance: Decimal
    status: ReconcileStatus


class ReconcileSummaryRow(BaseModel):
    period: str
    metric: str
    values: dict[str, Decimal]
    diffs: dict[str, Decimal]
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
    summary_rows: list[ReconcileSummaryRow] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime


class RunListItem(BaseModel):
    id: int
    rule_id: int
    rule_name: str
    start_date: date
    end_date: date
    granularity: Granularity
    status: str
    error_message: Optional[str] = None
    created_at: datetime


class BatchRunFailure(BaseModel):
    rule_id: int
    rule_name: str
    run: Optional[ReconcileRun] = None
    error_message: str


class BatchRunResponse(BaseModel):
    runs: list[ReconcileRun]
    failed_runs: list[BatchRunFailure]
    created_at: datetime


class BatchRunJob(BaseModel):
    job_id: str
    status: Literal["queued", "running", "cancel_requested", "cancelled", "completed"]
    total: int
    completed: int = 0
    total_steps: int = 0
    done_steps: int = 0
    progress_percent: int = 0
    stage: str = ""
    detail: str = ""
    current_period: str = ""
    current_page: Optional[int] = None
    current_rule_id: Optional[int] = None
    current_rule_name: str = ""
    runs: list[ReconcileRun] = Field(default_factory=list)
    failed_runs: list[BatchRunFailure] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime] = None
    cancel_requested_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class CompareExportRequest(BaseModel):
    run_ids: list[int] = Field(min_items=1)


class HealthResponse(BaseModel):
    status: str
    app: str
