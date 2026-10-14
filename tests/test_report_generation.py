"""Тесты генерации отчётов: PDF-черновик и Excel-выгрузка."""

from pathlib import Path


def _collect_demo_inputs():
    from src.config import DEMO_WELL_ID
    from tools.get_geo_report import get_geo_report
    from tools.get_production_data import get_production_data
    from tools.get_telemetry import get_telemetry
    from tools.list_wells import list_volve_periods, list_volve_wells

    name = list_volve_wells()[0]["well_name"]
    period = list_volve_periods(name)[0]
    prod = get_production_data(name, period, source="volve")
    tel = get_telemetry(DEMO_WELL_ID, "2026-09")
    geo = get_geo_report(DEMO_WELL_ID, "2026-09")
    return name, period, prod, tel, geo


def test_generate_report_draft(data_dir):
    from tools.generate_report_draft import generate_report_draft

    name, period, prod, tel, geo = _collect_demo_inputs()
    result = generate_report_draft(name, period, prod, tel, geo)

    assert result["status"] == "success", result.get("error")
    pdf_path = Path(result["data"]["pdf_path"])
    assert pdf_path.is_absolute()
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000
    assert isinstance(result["data"]["anomalies"], list)


def test_export_to_excel(data_dir):
    from tools.export_to_excel import export_to_excel

    name, period, prod, tel, geo = _collect_demo_inputs()
    result = export_to_excel(name, period, prod, tel, geo)

    assert result["status"] == "success", result.get("error")
    xlsx = Path(result["data"]["xlsx_path"])
    assert xlsx.is_absolute()
    assert xlsx.exists()
    assert xlsx.stat().st_size > 500
