from app.warehouse import _month_windows


def test_month_windows_clip_range_by_calendar_month() -> None:
    assert _month_windows("2026-01-15", "2026-03-05") == [
        ("2026-01", "2026-01-15", "2026-01-31"),
        ("2026-02", "2026-02-01", "2026-02-28"),
        ("2026-03", "2026-03-01", "2026-03-05"),
    ]


def test_month_windows_include_single_month_range() -> None:
    assert _month_windows("2026-05-01", "2026-05-31") == [
        ("2026-05", "2026-05-01", "2026-05-31"),
    ]
