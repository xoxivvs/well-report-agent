"""Тесты единого разбора отчётного периода."""

from datetime import datetime

import pytest

from src.periods import period_to_dates


def test_month_range():
    start, end = period_to_dates("2014-06")
    assert start == "2014-06-01"
    assert end == "2014-06-30"


def test_december_range():
    start, end = period_to_dates("2025-12")
    assert (start, end) == ("2025-12-01", "2025-12-31")


def test_single_day():
    assert period_to_dates("2014-06-25") == ("2014-06-25", "2014-06-25")


def test_last_week_resolves_to_seven_days():
    start, end = period_to_dates("last_week")
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    assert (e - s).days == 6
    assert s.weekday() == 0  # понедельник


@pytest.mark.parametrize("bad", ["не-период", "март 2026", "2014-13", "2014/06", ""])
def test_invalid_period_raises(bad):
    with pytest.raises(ValueError):
        period_to_dates(bad)
