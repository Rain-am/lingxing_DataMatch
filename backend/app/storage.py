from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

from app.config import get_settings
from app.schemas import ReconcileRow, ReconcileRun, Rule, RuleCreate, RuleUpdate


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
                error_message TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(rules)").fetchall()}
        if "erp_request_config_json" not in columns:
            conn.execute("ALTER TABLE rules ADD COLUMN erp_request_config_json TEXT NOT NULL DEFAULT '{}'")


def _rule_from_row(row: sqlite3.Row) -> Rule:
    data = dict(row)
    data["metrics"] = json.loads(data.pop("metrics_json"))
    data["erp_request_config"] = json.loads(data.pop("erp_request_config_json", "{}") or "{}")
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
    metrics_json = json.dumps([_model_json_dict(m) for m in payload.metrics], ensure_ascii=False)
    request_config_json = json.dumps(payload.erp_request_config, ensure_ascii=False)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO rules (
                name, warehouse_table, warehouse_date_field, warehouse_store_field,
                erp_module_path, erp_date_field, erp_store_field, erp_request_config_json, metrics_json,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.warehouse_table,
                payload.warehouse_date_field,
                payload.warehouse_store_field,
                payload.erp_module_path,
                payload.erp_date_field,
                payload.erp_store_field,
                request_config_json,
                metrics_json,
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
    metrics_json = json.dumps([_model_json_dict(m) for m in payload.metrics], ensure_ascii=False)
    request_config_json = json.dumps(payload.erp_request_config, ensure_ascii=False)
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE rules
            SET name = ?, warehouse_table = ?, warehouse_date_field = ?, warehouse_store_field = ?,
                erp_module_path = ?, erp_date_field = ?, erp_store_field = ?,
                erp_request_config_json = ?, metrics_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.name,
                payload.warehouse_table,
                payload.warehouse_date_field,
                payload.warehouse_store_field,
                payload.erp_module_path,
                payload.erp_date_field,
                payload.erp_store_field,
                request_config_json,
                metrics_json,
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
    error_message: Optional[str] = None,
) -> ReconcileRun:
    now = datetime.now().isoformat()
    rows_json = json.dumps([_model_json_dict(row) for row in rows], ensure_ascii=False)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reconcile_runs (
                rule_id, rule_name, start_date, end_date, granularity, status,
                rows_json, error_message, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule_id,
                rule_name,
                start_date.isoformat(),
                end_date.isoformat(),
                granularity,
                status,
                rows_json,
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
    return ReconcileRun.parse_obj(data)
