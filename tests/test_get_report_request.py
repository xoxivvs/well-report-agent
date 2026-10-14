"""Тесты инструмента get_report_request (разбор запроса)."""

import pytest

from tools.get_report_request import (
    get_report_request,
    parse_period,
    parse_report_type,
    parse_well_id,
)


@pytest.mark.parametrize("query,expected", [
    ("Отчёт по скважине 5 за март 2026", 5),
    ("Нужна сводка по скв-3", 3),
    ("Сделай отчёт по скважине №7", 7),
    ("Отчёт по пятой скважине", 5),
])
def test_parse_well_id_success(query, expected):
    assert parse_well_id(query) == expected


def test_parse_well_id_error():
    with pytest.raises(ValueError):
        parse_well_id("Привет, как дела?")


def test_parse_period_month_and_year():
    assert parse_period("Отчёт за январь 2024") == "2024-01"
    assert parse_period("сделай за декабрь 2025") == "2025-12"


@pytest.mark.parametrize("query,expected", [
    ("суточный отчёт", "daily"),
    ("отчёт за неделю", "weekly"),
    ("месячный отчёт", "monthly"),
])
def test_parse_report_type(query, expected):
    assert parse_report_type(query) == expected


def test_get_report_request_success():
    result = get_report_request("Сделай отчёт по скважине 5 за март 2026")
    assert result["status"] == "success"
    assert result["data"]["well_id"] == 5
    assert result["data"]["period"] == "2026-03"
    assert result["error"] is None


def test_get_report_request_error():
    result = get_report_request("Привет, как дела?")
    assert result["status"] == "error"
    assert result["data"] is None
    assert result["error"]
