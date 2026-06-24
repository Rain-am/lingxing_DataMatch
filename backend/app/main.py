from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.exporter import build_run_excel
from app.reconcile import build_reconcile_rows
from app.schemas import HealthResponse, ReconcileRun, Rule, RuleCreate, RuleUpdate, RunRequest
from app.storage import create_rule, delete_rule, get_rule, get_run, init_db, list_rules, save_run, update_rule
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


@app.post("/api/reconcile/run", response_model=ReconcileRun)
def api_run_reconcile(payload: RunRequest) -> ReconcileRun:
    rule = get_rule(payload.rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    try:
        rows = build_reconcile_rows(
            rule,
            payload.start_date.isoformat(),
            payload.end_date.isoformat(),
            payload.granularity,
        )
        return save_run(
            rule_id=rule.id,
            rule_name=rule.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            granularity=payload.granularity,
            rows=rows,
        )
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


@app.get("/api/reconcile/runs/{run_id}", response_model=ReconcileRun)
def api_get_run(run_id: int) -> ReconcileRun:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


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
