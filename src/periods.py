"""
Разбор отчётного периода в диапазон дат.

Единая валидация для всех инструментов: некорректный ввод
(«март 2026», «вчера», пустая строка) → ValueError, а вызывающий код
превращает это в статус "error" вместо тихого "empty".
"""

import re
from datetime import datetime, timedelta

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def period_to_dates(period: str) -> tuple[str, str]:
    """
    Приводит период к диапазону дат.

    Форматы:
    - "YYYY-MM"     → первый и последний день месяца;
    - "YYYY-MM-DD"  → один и тот же день (start == end).

    Returns:
        (start_date, end_date) в формате "YYYY-MM-DD".

    Raises:
        ValueError: период не соответствует одному из форматов.
    """
    text = str(period).strip()

    # Сентинель из get_report_request: «прошлый неделя» → реальный диапазон
    if text == "last_week":
        today = datetime.now()
        this_monday = today - timedelta(days=today.weekday())
        last_monday = this_monday - timedelta(days=7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d")

    month_match = _MONTH_RE.match(text)
    if month_match:
        year, month = int(month_match.group(1)), int(month_match.group(2))
        if not 1 <= month <= 12:
            raise ValueError(f"Месяц вне диапазона 01-12: {text}")
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year}-12-31"
        else:
            end = (datetime(year, month + 1, 1) - timedelta(days=1)).strftime("%Y-%m-%d")
        return start, end

    # YYYY-MM-DD или ошибка формата (strptime сам бросит ValueError)
    day = datetime.strptime(text, "%Y-%m-%d")
    date = day.strftime("%Y-%m-%d")
    return date, date
