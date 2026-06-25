from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

from app.config import get_settings
from app.schemas import ReconcileRow, ReconcileRun, RunListItem, Rule, RuleCreate, RuleUpdate, Source


def _model_json_dict(model):
    return json.loads(model.json())


def _db_path() -> Path:
    path = Path(get_settings().sqlite_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                warehouse_table TEXT NOT NULL,
                warehouse_date_field TEXT NOT NULL,
                warehouse_store_field TEXT NOT NULL,
                erp_module_path TEXT NOT NULL,
                erp_date_field TEXT NOT NULL,
                erp_store_field TEXT NOT NULL,
                erp_request_config_json TEXT NOT NULL DEFAULT '{}',
                metrics_json TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                comparison_base_source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reconcile_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER NOT NULL,
                rule_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                granularity TEXT NOT NULL,
                status TEXT NOT NULL,
                rows_json TEXT NOT NULL,
                summary_rows_json TEXT NOT NULL DEFAULT '[]',
                error_message TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(rules)").fetchall()}
        if "erp_request_config_json" not in columns:
            conn.execute("ALTER TABLE rules ADD COLUMN erp_request_config_json TEXT NOT NULL DEFAULT '{}'")
        if "sources_json" not in columns:
            conn.execute("ALTER TABLE rules ADD COLUMN sources_json TEXT NOT NULL DEFAULT '[]'")
        if "comparison_base_source" not in columns:
            conn.execute("ALTER TABLE rules ADD COLUMN comparison_base_source TEXT NOT NULL DEFAULT ''")
        run_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reconcile_runs)").fetchall()}
        if "summary_rows_json" not in run_columns:
            conn.execute("ALTER TABLE reconcile_runs ADD COLUMN summary_rows_json TEXT NOT NULL DEFAULT '[]'")


def _legacy_sources(data: dict) -> list[dict]:
    metrics = json.loads(data.get("metrics_json") or "[]")
    sources: list[dict] = []
    if data.get("warehouse_table"):
        sources.append(
            {
                "name": "数仓",
                "type": "warehouse",
                "table_or_path": data["warehouse_table"],
                "date_field": data.get("warehouse_date_field") or "",
                "store_field": data.get("warehouse_store_field") or "",
                "period_mode": "response_field",
                "request_config": {},
                "metrics": metrics,
            }
        )
    if data.get("erp_module_path"):
        sources.append(
            {
                "name": "ERP",
                "type": "erp",
                "table_or_path": data["erp_module_path"],
                "date_field": data.get("erp_date_field") or "",
                "store_field": data.get("erp_store_field") or "",
                "period_mode": "response_field",
                "request_config": json.loads(data.get("erp_request_config_json") or "{}"),
                "metrics": metrics,
            }
        )
    return sources


def _normalize_sources(payload: RuleCreate | RuleUpdate) -> list[Source]:
    if payload.sources:
        return payload.sources
    metrics = payload.metrics
    sources: list[Source] = []
    if payload.warehouse_table:
        sources.append(
            Source(
                name="数仓",
                type="warehouse",
                table_or_path=payload.warehouse_table,
                date_field=payload.warehouse_date_field,
                store_field=payload.warehouse_store_field,
                metrics=metrics,
            )
        )
    if payload.erp_module_path:
        sources.append(
            Source(
                name="ERP",
                type="erp",
                table_or_path=payload.erp_module_path,
                date_field=payload.erp_date_field,
                store_field=payload.erp_store_field,
                request_config=payload.erp_request_config,
                metrics=metrics,
            )
        )
    return sources


def _legacy_columns(payload: RuleCreate | RuleUpdate, sources: list[Source]) -> tuple[str, str, str, str, str, str]:
    warehouse = next((source for source in sources if source.type == "warehouse"), None)
    erp = next((source for source in sources if source.type == "erp"), None)
    return (
        payload.warehouse_table or (warehouse.table_or_path if warehouse else ""),
        payload.warehouse_date_field or (warehouse.date_field if warehouse else ""),
        payload.warehouse_store_field or (warehouse.store_field if warehouse else ""),
        payload.erp_module_path or (erp.table_or_path if erp else ""),
        payload.erp_date_field or (erp.date_field if erp else ""),
        payload.erp_store_field or (erp.store_field if erp else ""),
    )


def _rule_from_row(row: sqlite3.Row) -> Rule:
    data = dict(row)
    data["metrics"] = json.loads(data.pop("metrics_json"))
    data["erp_request_config"] = json.loads(data.pop("erp_request_config_json", "{}") or "{}")
    sources = json.loads(data.pop("sources_json", "[]") or "[]")
    data["sources"] = sources or _legacy_sources(dict(row))
    return Rule.parse_obj(data)


def list_rules() -> list[Rule]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM rules ORDER BY updated_at DESC, id DESC").fetchall()
    return [_rule_from_row(row) for row in rows]


def get_rule(rule_id: int) -> Optional[Rule]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
    return _rule_from_row(row) if row else None


def create_rule(payload: RuleCreate) -> Rule:
    now = datetime.now().isoformat()
    sources = _normalize_sources(payload)
    metrics = payload.metrics or (sources[0].metrics if sources else [])
    metrics_json = json.dumps([_model_json_dict(m) for m in metrics], ensure_ascii=False)
    sources_json = json.dumps([_model_json_dict(source) for source in sources], ensure_ascii=False)
    request_config_json = json.dumps(payload.erp_request_config, ensure_ascii=False)
    legacy = _legacy_columns(payload, sources)
    comparison_base_source = payload.comparison_base_source or (sources[0].name if sources else "")
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO rules (
                name, warehouse_table, warehouse_date_field, warehouse_store_field,
                erp_module_path, erp_date_field, erp_store_field, erp_request_config_json, metrics_json,
                sources_json, comparison_base_source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                legacy[0],
                legacy[1],
                legacy[2],
                legacy[3],
                legacy[4],
                legacy[5],
                request_config_json,
                metrics_json,
                sources_json,
                comparison_base_source,
                now,
                now,
            ),
        )
        rule_id = int(cursor.lastrowid)
    rule = get_rule(rule_id)
    assert rule is not None
    return rule


def update_rule(rule_id: int, payload: RuleUpdate) -> Optional[Rule]:
    now = datetime.now().isoformat()
    sources = _normalize_sources(payload)
    metrics = payload.metrics or (sources[0].metrics if sources else [])
    metrics_json = json.dumps([_model_json_dict(m) for m in metrics], ensure_ascii=False)
    sources_json = json.dumps([_model_json_dict(source) for source in sources], ensure_ascii=False)
    request_config_json = json.dumps(payload.erp_request_config, ensure_ascii=False)
    legacy = _legacy_columns(payload, sources)
    comparison_base_source = payload.comparison_base_source or (sources[0].name if sources else "")
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE rules
            SET name = ?, warehouse_table = ?, warehouse_date_field = ?, warehouse_store_field = ?,
                erp_module_path = ?, erp_date_field = ?, erp_store_field = ?,
                erp_request_config_json = ?, metrics_json = ?, sources_json = ?, comparison_base_source = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.name,
                legacy[0],
                legacy[1],
                legacy[2],
                legacy[3],
                legacy[4],
                legacy[5],
                request_config_json,
                metrics_json,
                sources_json,
                comparison_base_source,
                now,
                rule_id,
            ),
        )
    if cursor.rowcount == 0:
        return None
    return get_rule(rule_id)


def delete_rule(rule_id: int) -> bool:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
    return cursor.rowcount > 0


def save_run(
    *,
    rule_id: int,
    rule_name: str,
    start_date: date,
    end_date: date,
    granularity: str,
    rows: list[ReconcileRow],
    status: str = "success",
    summary_rows: Optional[list] = None,
    error_message: Optional[str] = None,
) -> ReconcileRun:
    now = datetime.now().isoformat()
    rows_json = json.dumps([_model_json_dict(row) for row in rows], ensure_ascii=False)
    summary_rows_json = json.dumps([_model_json_dict(row) for row in summary_rows or []], ensure_ascii=False)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reconcile_runs (
                rule_id, rule_name, start_date, end_date, granularity, status,
                rows_json, summary_rows_json, error_message, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule_id,
                rule_name,
                start_date.isoformat(),
                end_date.isoformat(),
                granularity,
                status,
                rows_json,
                summary_rows_json,
                error_message,
                now,
            ),
        )
        run_id = int(cursor.lastrowid)
    run = get_run(run_id)
    assert run is not None
    return run


def get_run(run_id: int) -> Optional[ReconcileRun]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM reconcile_runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["rows"] = json.loads(data.pop("rows_json"))
    data["summary_rows"] = json.loads(data.pop("summary_rows_json", "[]") or "[]")
    return ReconcileRun.parse_obj(data)


def delete_run(run_id: int) -> bool:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM reconcile_runs WHERE id = ?", (run_id,))
    return cursor.rowcount > 0


def list_runs(
    *,
    rule_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
) -> list[RunListItem]:
    clauses: list[str] = []
    params: list[object] = []
    if rule_id is not None:
        clauses.append("rule_id = ?")
        params.append(rule_id)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if start_date is not None:
        clauses.append("end_date >= ?")
        params.append(start_date.isoformat())
    if end_date is not None:
        clauses.append("start_date <= ?")
        params.append(end_date.isoformat())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, rule_id, rule_name, start_date, end_date, granularity, status, error_message, created_at
            FROM reconcile_runs
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [RunListItem.parse_obj(dict(row)) for row in rows]
