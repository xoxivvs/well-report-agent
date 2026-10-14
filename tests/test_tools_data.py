"""Тесты инструментов чтения данных: скважины, добыча, телеметрия, геология."""



def test_list_volve_wells(data_dir):
    from tools.list_wells import list_volve_wells

    wells = list_volve_wells()
    assert wells, "Ожидались скважины Volve"
    assert all({"well_name", "records"} <= set(w) for w in wells)


def test_list_volve_periods(volve_well):
    from tools.list_wells import list_volve_periods

    periods = list_volve_periods(volve_well["name"])
    assert periods
    assert all(len(p) >= 7 for p in periods)


def test_production_success(volve_well):
    from tools.get_production_data import get_production_data

    result = get_production_data(volve_well["name"], volve_well["period"], source="volve")
    assert result["status"] == "success"
    assert result["data"]["records"]


def test_production_empty(volve_well):
    from tools.get_production_data import get_production_data

    # Заведомо будущий период — данных нет, это законный «empty»
    result = get_production_data(volve_well["name"], "2099-01", source="volve")
    assert result["status"] in ("empty", "success")
    if result["status"] == "empty":
        assert result["error"] is None


def test_production_error_bad_source(volve_well):
    from tools.get_production_data import get_production_data

    result = get_production_data(volve_well["name"], volve_well["period"], source="nope")
    assert result["status"] == "error"
    assert result["error"]


def test_telemetry_returns_dict():
    from tools.get_telemetry import get_telemetry

    result = get_telemetry(5, "2026-09")
    assert result["status"] in ("success", "empty")
    assert set(result) == {"status", "data", "error"}


def test_telemetry_error_bad_period():
    from tools.get_telemetry import get_telemetry

    result = get_telemetry(5, "не-период")
    assert result["status"] == "error"
    assert result["error"]


def test_production_error_bad_period(volve_well):
    from tools.get_production_data import get_production_data

    result = get_production_data(volve_well["name"], "март 2026", source="volve")
    assert result["status"] == "error"
    assert "период" in result["error"].lower()


def test_geo_report_success():
    from tools.get_geo_report import get_geo_report

    result = get_geo_report(5, "2026-09")
    assert result["status"] == "success"
    assert result["data"]["reservoir_pressure"] > 0


def test_geo_report_empty():
    from tools.get_geo_report import get_geo_report

    result = get_geo_report(5, "1999-01")
    assert result["status"] == "empty"
    assert result["error"] is None
