from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.exporter import build_compare_excel, build_run_excel
from app.reconcile import build_reconcile_result
from app.schemas import (
    BatchRunFailure,
    BatchRunJob,
    BatchRunRequest,
    BatchRunResponse,
    CompareExportRequest,
    HealthResponse,
    ReconcileRun,
    Rule,
    RuleCreate,
    RuleUpdate,
    RunListItem,
    RunRequest,
)
from app.storage import (
    create_rule,
    delete_rule,
    delete_run,
    get_rule,
    get_run,
    init_db,
    list_rules,
    list_runs,
    save_run,
    update_rule,
)
from app.validation import validate_rule_payload

app = FastAPI(title="Lingxing Data Match", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


_batch_executor = ThreadPoolExecutor(max_workers=2)
_batch_jobs: dict[str, BatchRunJob] = {}
_batch_jobs_lock = Lock()


def _copy_batch_job(job: BatchRunJob) -> BatchRunJob:
    if hasattr(job, "model_copy"):
        return job.model_copy(deep=True)
    return job.copy(deep=True)


def _save_batch_job(job: BatchRunJob) -> None:
    job.updated_at = datetime.now()
    with _batch_jobs_lock:
        _batch_jobs[job.job_id] = _copy_batch_job(job)


def _get_batch_job(job_id: str) -> Optional[BatchRunJob]:
    with _batch_jobs_lock:
        job = _batch_jobs.get(job_id)
        return _copy_batch_job(job) if job else None


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=get_settings().app_name)


@app.get("/")
def frontend_index() -> FileResponse:
    index_path = FRONTEND_DIST / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend dist not found; run frontend build first")
    return FileResponse(index_path)


@app.get("/api/rules", response_model=list[Rule])
def api_list_rules() -> list[Rule]:
    return list_rules()


@app.post("/api/rules", response_model=Rule)
def api_create_rule(payload: RuleCreate) -> Rule:
    validate_rule_payload(payload)
    return create_rule(payload)


@app.put("/api/rules/{rule_id}", response_model=Rule)
def api_update_rule(rule_id: int, payload: RuleUpdate) -> Rule:
    validate_rule_payload(payload)
    rule = update_rule(rule_id, payload)
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    return rule


@app.delete("/api/rules/{rule_id}")
def api_delete_rule(rule_id: int) -> dict[str, bool]:
    if not delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="rule not found")
    return {"ok": True}


def _run_rule(rule: Rule, start_date: date, end_date: date, granularity: str) -> ReconcileRun:
    rows, summary_rows = build_reconcile_result(
        rule,
        start_date.isoformat(),
        end_date.isoformat(),
        granularity,
    )
    return save_run(
        rule_id=rule.id,
        rule_name=rule.name,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        rows=rows,
        summary_rows=summary_rows,
    )


@app.post("/api/reconcile/run", response_model=ReconcileRun)
def api_run_reconcile(payload: RunRequest) -> ReconcileRun:
    rule = get_rule(payload.rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    try:
        return _run_rule(rule, payload.start_date, payload.end_date, payload.granularity)
    except Exception as exc:
        run = save_run(
            rule_id=rule.id,
            rule_name=rule.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            granularity=payload.granularity,
            rows=[],
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(status_code=500, detail={"message": "reconcile failed", "run": jsonable_encoder(run)})


@app.post("/api/reconcile/batch-run", response_model=BatchRunResponse)
def api_batch_run_reconcile(payload: BatchRunRequest) -> BatchRunResponse:
    runs: list[ReconcileRun] = []
    failed_runs: list[BatchRunFailure] = []
    for rule_id in payload.rule_ids:
        rule = get_rule(rule_id)
        if not rule:
            failed_runs.append(BatchRunFailure(rule_id=rule_id, rule_name="", error_message="rule not found"))
            continue
        try:
            runs.append(_run_rule(rule, payload.start_date, payload.end_date, payload.granularity))
        except Exception as exc:
            failed_run = save_run(
                rule_id=rule.id,
                rule_name=rule.name,
                start_date=payload.start_date,
                end_date=payload.end_date,
                granularity=payload.granularity,
                rows=[],
                status="failed",
                error_message=str(exc),
            )
            failed_runs.append(
                BatchRunFailure(rule_id=rule.id, rule_name=rule.name, run=failed_run, error_message=str(exc))
            )
    return BatchRunResponse(runs=runs, failed_runs=failed_runs, created_at=datetime.now())


def _execute_batch_job(job_id: str, payload: BatchRunRequest) -> None:
    job = _get_batch_job(job_id)
    if not job:
        return
    job.status = "running"
    _save_batch_job(job)
    for rule_id in payload.rule_ids:
        rule = get_rule(rule_id)
        job.current_rule_id = rule_id
        job.current_rule_name = rule.name if rule else ""
        _save_batch_job(job)
        if not rule:
            job.failed_runs.append(BatchRunFailure(rule_id=rule_id, rule_name="", error_message="rule not found"))
            job.completed += 1
            _save_batch_job(job)
            continue
        try:
            job.runs.append(_run_rule(rule, payload.start_date, payload.end_date, payload.granularity))
        except Exception as exc:
            failed_run = save_run(
                rule_id=rule.id,
                rule_name=rule.name,
                start_date=payload.start_date,
                end_date=payload.end_date,
                granularity=payload.granularity,
                rows=[],
                status="failed",
                error_message=str(exc),
            )
            job.failed_runs.append(
                BatchRunFailure(rule_id=rule.id, rule_name=rule.name, run=failed_run, error_message=str(exc))
            )
        finally:
            job.completed += 1
            _save_batch_job(job)
    job.status = "completed"
    job.current_rule_id = None
    job.current_rule_name = ""
    job.finished_at = datetime.now()
    _save_batch_job(job)


@app.post("/api/reconcile/batch-run/jobs", response_model=BatchRunJob)
def api_create_batch_run_job(payload: BatchRunRequest) -> BatchRunJob:
    now = datetime.now()
    job = BatchRunJob(
        job_id=uuid4().hex,
        status="queued",
        total=len(payload.rule_ids),
        created_at=now,
        updated_at=now,
    )
    _save_batch_job(job)
    _batch_executor.submit(_execute_batch_job, job.job_id, payload)
    return job


@app.get("/api/reconcile/batch-run/jobs/{job_id}", response_model=BatchRunJob)
def api_get_batch_run_job(job_id: str) -> BatchRunJob:
    job = _get_batch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="batch job not found")
    return job


@app.get("/api/reconcile/runs", response_model=list[RunListItem])
def api_list_runs(
    rule_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[RunListItem]:
    return list_runs(rule_id=rule_id, status=status, start_date=start_date, end_date=end_date, limit=limit)


@app.post("/api/reconcile/runs/compare/export")
def api_export_compare(payload: CompareExportRequest) -> StreamingResponse:
    runs: list[ReconcileRun] = []
    for run_id in payload.run_ids:
        run = get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"run {run_id} not found")
        runs.append(run)
    stream = build_compare_excel(runs)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="reconcile-compare.xlsx"'},
    )


@app.get("/api/reconcile/runs/{run_id}", response_model=ReconcileRun)
def api_get_run(run_id: int) -> ReconcileRun:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.delete("/api/reconcile/runs/{run_id}")
def api_delete_run(run_id: int) -> dict[str, bool]:
    if not delete_run(run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return {"ok": True}


@app.get("/api/reconcile/runs/{run_id}/export")
def api_export_run(run_id: int) -> StreamingResponse:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    stream = build_run_excel(run)
    filename = f"reconcile-run-{run.id}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
