"""
Инструмент 1: get_report_request
Восприятие задачи — разбор запроса инженера.
Извлекает из текста: номер скважины, период, тип отчёта.
"""

import re
from datetime import datetime, timedelta


def parse_period(text: str) -> str:
    """
    Определяет период отчёта из текста запроса.
    Возвращает строку в формате YYYY-MM или 'last_month', 'last_week'.
    """
    text_lower = text.lower()

    # Явно указанный месяц и год
    months = {
        "январ": "01", "феврал": "02", "март": "03", "апрел": "04",
        "ма": "05", "июн": "06", "июл": "07", "август": "08",
        "сентябр": "09", "октябр": "10", "ноябр": "11", "декабр": "12"
    }
    year_match = re.search(r"20\d{2}", text_lower)
    for key, num in months.items():
        if key in text_lower:
            year = year_match.group(0) if year_match else str(datetime.now().year)
            return f"{year}-{num}"

    # Относительные периоды
    if "прошл" in text_lower and "месяц" in text_lower:
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        return last_month.strftime("%Y-%m")
    if "прошл" in text_lower and "недел" in text_lower:
        return "last_week"
    if "сегодня" in text_lower or "сутк" in text_lower:
        return datetime.now().strftime("%Y-%m-%d")
    if "тек" in text_lower and "месяц" in text_lower:
        return datetime.now().strftime("%Y-%m")

    # По умолчанию — текущий месяц
    return datetime.now().strftime("%Y-%m")


def parse_well_id(text: str) -> int:
    """
    Извлекает номер скважины из текста.
    Ищет паттерны: 'скважина 5', 'скв-5', '№5', 'пятой скважины'.
    """
    patterns = [
        r"скв[а-я]*[\s\-]*№?\s*(\d+)",   # скважина 5, скв-5, скв №5
        r"№\s*(\d+)",                     # №5
        r"(\d+)[- ]?й\s+скважин",         # 5-й скважины
    ]
    text_lower = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return int(match.group(1))

    # Словесные числительные
    words = {
        "перв": 1, "втор": 2, "трет": 3, "четверт": 4, "пят": 5,
        "шест": 6, "седьм": 7, "восьм": 8, "девят": 9, "десят": 10
    }
    for key, num in words.items():
        if key in text_lower and "скважин" in text_lower:
            return num

    raise ValueError(f"Не удалось извлечь номер скважины из запроса: «{text}»")


def parse_report_type(text: str) -> str:
    """Определяет тип отчёта: суточный, недельный, месячный."""
    text_lower = text.lower()
    if "сут" in text_lower or "день" in text_lower:
        return "daily"
    if "недел" in text_lower:
        return "weekly"
    if "месяц" in text_lower:
        return "monthly"
    return "monthly"  # по умолчанию


def get_report_request(query: str) -> dict:
    """
    Главная функция инструмента.
    Возвращает структурированный результат разбора запроса.

    Returns:
        dict: {
            "status": "success" | "error",
            "data": {"well_id": int, "period": str, "report_type": str},
            "error": str | None
        }
    """
    try:
        well_id = parse_well_id(query)
        period = parse_period(query)
        report_type = parse_report_type(query)

        return {
            "status": "success",
            "data": {
                "well_id": well_id,
                "period": period,
                "report_type": report_type
            },
            "error": None
        }
    except ValueError as e:
        return {
            "status": "error",
            "data": None,
            "error": str(e)
        }


# --- Тесты для локальной проверки ---
if __name__ == "__main__":
    test_queries = [
        "Сделай отчёт по скважине 5 за март 2026",
        "Нужна сводка по скв-3 за прошлый месяц",
        "Отчёт по пятой скважине за неделю",
        "Сделай суточный отчёт по скважине №7",
        "Привет, как дела?",  # должен быть error
    ]

    for q in test_queries:
        result = get_report_request(q)
        print(f"\nЗапрос: {q}")
        print(f"Результат: {result}")
