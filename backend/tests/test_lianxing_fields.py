from decimal import Decimal

from app.lianxing_api import _field_value, _store_value, fetch_erp_source_values
from app.schemas import Metric, Source


def test_field_value_supports_nested_data_path() -> None:
    record = {"data": {"sids": [110], "gross_profit": "12.5"}}

    assert _field_value(record, "data>>gross_profit") == "12.5"
    assert _field_value(record, "data.sids") == [110]
    assert _store_value(record, "data>>sids") == "110"


def test_fetch_erp_source_values_uses_nested_store_and_metric_fields() -> None:
    class FakeClient:
        def fetch_source_records(self, source, start_date, end_date, granularity):
            return [{"_request_period": "2026-05-01", "data": {"sids": [110], "gross_profit": "12.5"}}]

    source = Source(
        name="ERP",
        type="erp",
        table_or_path="/basicOpen/finance/mreport/OrderProfit",
        date_field="",
        store_field="data>>sids",
        period_mode="request_month",
        metrics=[Metric(name="毛利润", warehouse_expression="gross_profit", erp_field="data>>gross_profit")],
    )

    assert fetch_erp_source_values(source, "2026-05-01", "2026-05-31", "month", client=FakeClient()) == {
        ("2026-05-01", "110", "毛利润", "ERP"): Decimal("12.5")
    }
