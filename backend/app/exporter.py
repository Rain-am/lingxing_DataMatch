from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from app.schemas import ReconcileRun


def build_run_excel(run: ReconcileRun) -> BytesIO:
    workbook = Workbook()
    result_sheet = workbook.active
    result_sheet.title = "对账结果"
    result_sheet.append(["周期", "店铺", "指标", "数仓值", "ERP值", "差异值", "差异率", "容差", "状态"])
    for cell in result_sheet[1]:
        cell.font = Font(bold=True)

    fills = {
        "matched": PatternFill("solid", fgColor="DDEEDF"),
        "minor_diff": PatternFill("solid", fgColor="FFF2CC"),
        "major_diff": PatternFill("solid", fgColor="F4CCCC"),
    }
    for row in run.rows:
        result_sheet.append(
            [
                row.period,
                row.store,
                row.metric,
                float(row.warehouse_value),
                float(row.erp_value),
                float(row.diff_value),
                float(row.diff_rate) if row.diff_rate is not None else None,
                float(row.tolerance),
                row.status,
            ]
        )
        fill = fills.get(row.status)
        if fill:
            for cell in result_sheet[result_sheet.max_row]:
                cell.fill = fill

    for column in result_sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        result_sheet.column_dimensions[column[0].column_letter].width = min(max(max_length + 2, 10), 28)

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

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream
