from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from app.schemas import ReconcileRun


def _autosize(sheet) -> None:
    for column in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        sheet.column_dimensions[column[0].column_letter].width = min(max(max_length + 2, 10), 28)


def build_run_excel(run: ReconcileRun) -> BytesIO:
    workbook = Workbook()

    summary_sheet = workbook.active
    summary_sheet.title = "横向汇总"
    sources = sorted({source for row in run.summary_rows for source in row.values})
    diff_sources = sorted({source for row in run.summary_rows for source in row.diffs})
    summary_sheet.append(["周期", "指标", *sources, *[f"差异-{source}" for source in diff_sources], "状态"])
    for cell in summary_sheet[1]:
        cell.font = Font(bold=True)
    for row in run.summary_rows:
        summary_sheet.append(
            [
                row.period,
                row.metric,
                *[float(row.values.get(source, 0)) for source in sources],
                *[float(row.diffs.get(source, 0)) for source in diff_sources],
                row.status,
            ]
        )

    detail_sheet = workbook.create_sheet("店铺明细")
    detail_sheet.append(["周期", "店铺", "指标", "来源", "值", "基准值", "差异值", "差异率", "容差", "状态"])
    for cell in detail_sheet[1]:
        cell.font = Font(bold=True)

    fills = {
        "matched": PatternFill("solid", fgColor="DDEEDF"),
        "minor_diff": PatternFill("solid", fgColor="FFF2CC"),
        "major_diff": PatternFill("solid", fgColor="F4CCCC"),
    }
    for row in run.rows:
        detail_sheet.append(
            [
                row.period,
                row.store,
                row.metric,
                row.source,
                float(row.value),
                float(row.warehouse_value),
                float(row.diff_value),
                float(row.diff_rate) if row.diff_rate is not None else None,
                float(row.tolerance),
                row.status,
            ]
        )
        fill = fills.get(row.status)
        if fill:
            for cell in detail_sheet[detail_sheet.max_row]:
                cell.fill = fill

    params_sheet = workbook.create_sheet("运行参数")
    params_sheet.append(["参数", "值"])
    params_sheet.append(["运行ID", run.id])
    params_sheet.append(["规则ID", run.rule_id])
    params_sheet.append(["规则名称", run.rule_name])
    params_sheet.append(["开始日期", run.start_date.isoformat()])
    params_sheet.append(["结束日期", run.end_date.isoformat()])
    params_sheet.append(["粒度", run.granularity])
    params_sheet.append(["状态", run.status])
    params_sheet.append(["错误信息", run.error_message or ""])
    for cell in params_sheet[1]:
        cell.font = Font(bold=True)

    for sheet in (summary_sheet, detail_sheet, params_sheet):
        _autosize(sheet)

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream
