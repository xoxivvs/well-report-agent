"""
Инструмент 3: get_telemetry
Восприятие — чтение телеметрии УЭЦН из SQLite.

Возвращает:
- наработку насоса на конец периода
- список тревог (alarm_code) за период
- количество тревог по типам
"""

import sqlite3

if __package__ in (None, ""):  # прямой запуск: python tools/get_telemetry.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DB_PATH
from src.periods import period_to_dates


def _period_to_dates(period: str) -> tuple:
    """
    Преобразует YYYY-MM или YYYY-MM-DD в диапазон дат.
    Некорректный формат → ValueError (вызывающий код вернёт "error").
    """
    start, end = period_to_dates(period)
    return f"{start} 00:00:00", f"{end} 23:59:59"


def get_telemetry(well_id: int, period: str) -> dict:
    """
    Возвращает телеметрию УЭЦН за период.

    Args:
        well_id: номер скважины
        period: 'YYYY-MM' или 'YYYY-MM-DD'

    Returns:
        dict: {
            "status": "success" | "empty" | "error",
            "data": {
                "well_id": int,
                "period": str,
                "runtime_end": float,
                "alarms": [...],
                "alarms_summary": {"OVERHEAT": 2, ...}
            },
            "error": str | None
        }
    """
    try:
        start_ts, end_ts = _period_to_dates(period)
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": f"Некорректный период: {period} ({e})"
        }

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute("""
            SELECT timestamp, runtime_hours, alarm_code
            FROM telemetry
            WHERE well_id = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """, (well_id, start_ts, end_ts)).fetchall()

        conn.close()

        if not rows:
            return {
                "status": "empty",
                "data": {
                    "well_id": well_id,
                    "period": period,
                    "runtime_end": None,
                    "alarms": [],
                    "alarms_summary": {}
                },
                "error": None
            }

        records = [dict(row) for row in rows]
        runtime_end = records[-1]["runtime_hours"]

        alarms = [r for r in records if r["alarm_code"]]
        alarms_summary = {}
        for alarm in alarms:
            code = alarm["alarm_code"]
            alarms_summary[code] = alarms_summary.get(code, 0) + 1

        return {
            "status": "success",
            "data": {
                "well_id": well_id,
                "period": period,
                "runtime_end": runtime_end,
                "alarms": alarms,
                "alarms_summary": alarms_summary
            },
            "error": None
        }

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": f"Ошибка БД: {e}"
        }


# --- Локальный тест ---
if __name__ == "__main__":
    tests = [
        (5, "2026-09"),
        (5, "2020-01"),
    ]

    for well_id, period in tests:
        result = get_telemetry(well_id, period)
        print(f"\nСкважина {well_id}, период {period}")
        print(f"Статус: {result['status']}")
        if result["status"] == "success":
            d = result["data"]
            print(f"  Наработка на конец периода: {d['runtime_end']} ч")
            print(f"  Тревог всего: {len(d['alarms'])}")
            print(f"  По типам: {d['alarms_summary']}")
        else:
            print(f"  Данные: {result['data']}")
            print(f"  Ошибка: {result['error']}")
