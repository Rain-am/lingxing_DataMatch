from datetime import date, datetime
from time import sleep

from fastapi.testclient import TestClient

from app import main
from app.schemas import ReconcileRun, Rule


def _rule(rule_id: int) -> Rule:
    now = datetime.now()
    return Rule(
        id=rule_id,
        name=f"规则{rule_id}",
        warehouse_table="warehouse_table",
        warehouse_date_field="biz_date",
        warehouse_store_field="store",
        erp_module_path="/example",
        erp_date_field="date",
        erp_store_field="store",
        erp_request_config={},
        metrics=[],
        sources=[],
        comparison_base_source="",
        created_at=now,
        updated_at=now,
    )


def _run(rule: Rule, start_date: date, end_date: date, granularity: str, progress_callback=None) -> ReconcileRun:
    if progress_callback:
        progress_callback(stage="测试取数", detail=rule.name, advance=1)
        progress_callback(stage="测试聚合", detail=rule.name, advance=1)
        progress_callback(stage="测试保存", detail=rule.name, advance=1)
    return ReconcileRun(
        id=rule.id + 100,
        rule_id=rule.id,
        rule_name=rule.name,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        status="success",
        rows=[],
        summary_rows=[],
        created_at=datetime.now(),
    )


def test_batch_run_job_completes(monkeypatch) -> None:
    monkeypatch.setattr(main, "get_rule", _rule)
    monkeypatch.setattr(main, "_run_rule", _run)
    client = TestClient(main.app)

    response = client.post(
        "/api/reconcile/batch-run/jobs",
        json={
            "rule_ids": [1, 2],
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
            "granularity": "month",
        },
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    for _ in range(20):
        job = client.get(f"/api/reconcile/batch-run/jobs/{job_id}").json()
        if job["status"] == "completed":
            break
        sleep(0.01)
    assert job["status"] == "completed"
    assert job["completed"] == 2
    assert job["progress_percent"] == 100
    assert [run["rule_id"] for run in job["runs"]] == [1, 2]


def test_cancel_missing_batch_job_returns_404() -> None:
    client = TestClient(main.app)

    response = client.post("/api/reconcile/batch-run/jobs/missing/cancel")

    assert response.status_code == 404


def test_cancel_completed_batch_job_keeps_completed(monkeypatch) -> None:
    monkeypatch.setattr(main, "get_rule", _rule)
    monkeypatch.setattr(main, "_run_rule", _run)
    client = TestClient(main.app)

    response = client.post(
        "/api/reconcile/batch-run/jobs",
        json={
            "rule_ids": [3],
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
            "granularity": "month",
        },
    )
    job_id = response.json()["job_id"]
    for _ in range(20):
        job = client.get(f"/api/reconcile/batch-run/jobs/{job_id}").json()
        if job["status"] == "completed":
            break
        sleep(0.01)

    response = client.post(f"/api/reconcile/batch-run/jobs/{job_id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_cancel_running_batch_job_stops_before_next_rule(monkeypatch) -> None:
    calls: list[int] = []

    def slow_run(rule: Rule, start_date: date, end_date: date, granularity: str, progress_callback=None) -> ReconcileRun:
        calls.append(rule.id)
        for index in range(20):
            if progress_callback:
                progress_callback(stage="测试慢任务", detail=f"{rule.name}-{index}")
            sleep(0.01)
        return _run(rule, start_date, end_date, granularity, progress_callback)

    monkeypatch.setattr(main, "get_rule", _rule)
    monkeypatch.setattr(main, "_run_rule", slow_run)
    client = TestClient(main.app)

    response = client.post(
        "/api/reconcile/batch-run/jobs",
        json={
            "rule_ids": [4, 5],
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
            "granularity": "month",
        },
    )
    job_id = response.json()["job_id"]
    sleep(0.03)

    response = client.post(f"/api/reconcile/batch-run/jobs/{job_id}/cancel")

    assert response.status_code == 200
    for _ in range(40):
        job = client.get(f"/api/reconcile/batch-run/jobs/{job_id}").json()
        if job["status"] == "cancelled":
            break
        sleep(0.01)
    assert job["status"] == "cancelled"
    assert calls == [4]
