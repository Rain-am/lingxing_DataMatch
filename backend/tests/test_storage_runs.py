from datetime import date

from app import storage


def test_list_runs_returns_newest_first(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "runs.db"
    monkeypatch.setattr(storage, "get_settings", lambda: type("Settings", (), {"sqlite_path": str(db_path)})())
    storage.init_db()

    storage.save_run(
        rule_id=1,
        rule_name="规则A",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        granularity="month",
        rows=[],
    )
    storage.save_run(
        rule_id=2,
        rule_name="规则B",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        granularity="month",
        rows=[],
    )

    runs = storage.list_runs()

    assert [run.rule_name for run in runs] == ["规则B", "规则A"]
    assert storage.list_runs(rule_id=1)[0].rule_name == "规则A"
