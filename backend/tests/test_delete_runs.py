from datetime import date

from app import storage


def test_delete_run_removes_only_target_run(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "runs.db"
    monkeypatch.setattr(storage, "get_settings", lambda: type("Settings", (), {"sqlite_path": str(db_path)})())
    storage.init_db()

    first = storage.save_run(
        rule_id=1,
        rule_name="Rule A",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        granularity="month",
        rows=[],
    )
    second = storage.save_run(
        rule_id=2,
        rule_name="Rule B",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        granularity="month",
        rows=[],
    )

    assert storage.delete_run(first.id) is True
    assert storage.get_run(first.id) is None
    assert storage.get_run(second.id) is not None
    assert storage.delete_run(first.id) is False
