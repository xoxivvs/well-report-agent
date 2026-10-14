"""
Инструмент 2: get_production_data
Восприятие — чтение данных о добыче.

Поддерживает два источника:
- source="volve"     → реальные данные Volve (production_volve)
- source="synthetic" → синтетические данные (production)
"""

import sqlite3

if __package__ in (None, ""):  # прямой запуск: python tools/get_production_data.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DB_PATH
from src.periods import period_to_dates


def _period_to_dates(period: str) -> tuple:
    """YYYY-MM или YYYY-MM-DD → (start, end). Некорректный формат → ValueError."""
    return period_to_dates(period)


def _get_volve_data(well_name: str, start: str, end: str) -> dict:
    """Данные Volve за период."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT date, on_stream_hours, oil_volume, gas_volume, water_volume,
               water_cut, downhole_pressure, wellhead_pressure, choke_size
        FROM production_volve
        WHERE well_name = ? AND date BETWEEN ? AND ?
        ORDER BY date ASC
    """, (well_name, start, end)).fetchall()

    conn.close()

    if not rows:
        return {
            "status": "empty",
            "data": {
                "well_name": well_name,
                "period": f"{start} → {end}",
                "records": [],
                "aggregates": None,
                "trend": None,
            },
            "error": None,
        }

    records = [dict(r) for r in rows]
    working = [r for r in records if (r["on_stream_hours"] or 0) > 0]

    if not working:
        return {
            "status": "empty",
            "data": {
                "well_name": well_name,
                "period": f"{start} → {end}",
                "records": records,
                "aggregates": {
                    "days_count": len(records),
                    "working_days": 0,
                    "avg_oil": 0,
                    "avg_water_cut": 0,
                    "total_oil": 0,
                },
                "trend": None,
            },
            "error": None,
        }

    oil_values = [r["oil_volume"] for r in working]
    water_cuts = [r["water_cut"] for r in working]

    aggregates = {
        "days_count": len(records),
        "working_days": len(working),
        "avg_oil": round(sum(oil_values) / len(oil_values), 2),
        "avg_water_cut": round(sum(water_cuts) / len(water_cuts), 2),
        "total_oil": round(sum(oil_values), 2),
        "max_oil": round(max(oil_values), 2),
        "min_oil": round(min(oil_values), 2),
    }

    # Тренд: 1-я половина vs 2-я половина
    mid = len(oil_values) // 2
    if mid > 0:
        first_avg = sum(oil_values[:mid]) / mid
        second_avg = sum(oil_values[mid:]) / (len(oil_values) - mid)
        delta = round(second_avg - first_avg, 2)
        trend = {
            "delta_oil": delta,
            "direction": "рост" if delta > 5 else ("падение" if delta < -5 else "стабильно"),
            "first_half_avg": round(first_avg, 2),
            "second_half_avg": round(second_avg, 2),
        }
    else:
        trend = {"delta_oil": 0, "direction": "стабильно"}

    return {
        "status": "success",
        "data": {
            "well_name": well_name,
            "period": f"{start} → {end}",
            "records": records,
            "aggregates": aggregates,
            "trend": trend,
        },
        "error": None,
    }


def _get_synthetic_data(well_id: int, start: str, end: str) -> dict:
    """Старая логика для синтетики (оставляем на всякий случай)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT date, liquid_rate, oil_rate, water_cut
        FROM production
        WHERE well_id = ? AND date BETWEEN ? AND ?
        ORDER BY date ASC
    """, (well_id, start, end)).fetchall()

    conn.close()

    if not rows:
        return {"status": "empty", "data": None, "error": None}

    records = [dict(r) for r in rows]
    oil_rates = [r["oil_rate"] for r in records]
    water_cuts = [r["water_cut"] for r in records]

    aggregates = {
        "days_count": len(records),
        "working_days": len(records),
        "avg_oil": round(sum(oil_rates) / len(oil_rates), 2),
        "avg_water_cut": round(sum(water_cuts) / len(water_cuts), 2),
        "total_oil": round(sum(oil_rates), 2),
    }

    mid = len(records) // 2
    first_avg = sum(oil_rates[:mid]) / mid if mid > 0 else 0
    second_avg = sum(oil_rates[mid:]) / (len(records) - mid) if len(records) > mid else 0
    delta = round(second_avg - first_avg, 2)

    return {
        "status": "success",
        "data": {
            "well_id": well_id,
            "records": records,
            "aggregates": aggregates,
            "trend": {
                "delta_oil": delta,
                "direction": "рост" if delta > 1 else ("падение" if delta < -1 else "стабильно"),
            },
        },
        "error": None,
    }


def get_production_data(well_identifier, period: str, source: str = "volve") -> dict:
    """
    Главная функция.

    Args:
        well_identifier: для source="volve" — имя скважины (str),
                         для source="synthetic" — well_id (int)
        period: YYYY-MM
        source: "volve" | "synthetic"

    Returns:
        dict со статусом success/empty/error
    """
    try:
        start, end = _period_to_dates(period)
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": f"Некорректный период: {period} ({e})",
        }

    try:
        if source == "volve":
            return _get_volve_data(str(well_identifier), start, end)
        else:
            return _get_synthetic_data(int(well_identifier), start, end)
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": f"Ошибка БД: {e}",
        }


# --- Локальный тест ---
if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ VOLVE (реальные данные)")
    print("=" * 60)

    for well_name, period in [
        ("15/9-F-14", "2014-06"),
        ("15/9-F-14", "2008-06"),
        ("15/9-F-12", "2015-03"),
    ]:
        result = get_production_data(well_name, period, source="volve")
        print(f"\n{well_name} / {period}")
        print(f"  Статус: {result['status']}")
        if result["status"] == "success":
            agg = result["data"]["aggregates"]
            tr = result["data"]["trend"]
            print(f"  Дней: {agg['days_count']} (рабочих: {agg['working_days']})")
            print(f"  Средний дебит нефти: {agg['avg_oil']} м³/сут")
            print(f"  Средняя обводнённость: {agg['avg_water_cut']}%")
            print(f"  Суммарная добыча: {agg['total_oil']} м³")
            print(f"  Тренд: {tr['direction']} ({tr['delta_oil']})")
        else:
            print(f"  Ошибка: {result['error']}")

    print("\n" + "=" * 60)
    print("ТЕСТ СИНТЕТИКИ (для совместимости)")
    print("=" * 60)

    result = get_production_data(5, "2026-09", source="synthetic")
    print("\nСкважина 5 / 2026-09 (synthetic)")
    print(f"  Статус: {result['status']}")
    if result["status"] == "success":
        print(f"  Средний дебит: {result['data']['aggregates']['avg_oil']} т/сут")

"""
Инструмент: обнаружение аномалий на данных Volve.
Трендовая логика: сравнение с 14-дневным скользящим средним.
"""


def _moving_average(values, window=14):
    if len(values) < window:
        return values
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(sum(values[start:i + 1]) / (i - start + 1))
    return result


def _detect_trend(values):
    if len(values) < 10:
        return "стабильно"
    mid = len(values) // 2
    first = sum(values[:mid]) / mid
    second = sum(values[mid:]) / (len(values) - mid)
    delta_pct = (second - first) / first * 100 if first > 0 else 0
    if delta_pct > 10:
        return "рост"
    elif delta_pct < -10:
        return "падение"
    return "стабильно"


def detect_anomalies_volve(production_data):
    anomalies = []

    if production_data["status"] != "success":
        return {"anomalies": [], "summary": "Недостаточно данных для анализа."}

    records = [r for r in production_data["data"]["records"] if (r["on_stream_hours"] or 0) > 0]
    if len(records) < 5:
        return {"anomalies": [], "summary": "Слишком мало рабочих дней для анализа."}

    oil_values = [r["oil_volume"] for r in records]
    water_cuts = [r["water_cut"] for r in records]

    ma_oil = _moving_average(oil_values, window=14)
    ma_water = _moving_average(water_cuts, window=14)

    # 1. Резкие падения дебита
    for i in range(len(records)):
        if ma_oil[i] > 0 and oil_values[i] < ma_oil[i] * 0.4:
            date = records[i]["date"]
            drop_pct = round((1 - oil_values[i] / ma_oil[i]) * 100, 1)
            anomalies.append({
                "type": "резкое_падение_дебита",
                "severity": "высокая",
                "date": date,
                "description": (
                    f"{date}: дебит нефти упал до {oil_values[i]:.0f} м³/сут — "
                    f"на {drop_pct}% ниже 14-дневного среднего ({ma_oil[i]:.0f} м³/сут). "
                    f"Возможные причины: срыв подачи, остановка, ограничение штуцера."
                ),
            })

    # 2. Скачки обводнённости
    for i in range(len(records)):
        if abs(water_cuts[i] - ma_water[i]) > 15:
            date = records[i]["date"]
            delta = water_cuts[i] - ma_water[i]
            anomalies.append({
                "type": "скачок_обводнённости",
                "severity": "средняя",
                "date": date,
                "description": (
                    f"{date}: обводнённость изменилась на {delta:+.1f}% "
                    f"(текущая {water_cuts[i]:.1f}%, средняя {ma_water[i]:.1f}%)."
                ),
            })

    # 3. Длительные простои
    all_records = production_data["data"]["records"]
    current = 0
    start = None
    long_stops = []
    for r in all_records:
        if (r["on_stream_hours"] or 0) == 0:
            if current == 0:
                start = r["date"]
            current += 1
        else:
            if current >= 7:
                long_stops.append((start, r["date"], current))
            current = 0

    for start_date, end_date, days in long_stops[:3]:
        anomalies.append({
            "type": "длительный_простой",
            "severity": "средняя",
            "date": start_date,
            "description": (
                f"Простой с {start_date} по {end_date} — {days} дней подряд."
            ),
        })

    # 4. Тренд
    trend = _detect_trend(oil_values)
    if trend == "падение":
        mid = len(oil_values) // 2
        first_avg = sum(oil_values[:mid]) / mid
        last_avg = sum(oil_values[mid:]) / (len(oil_values) - mid)
        drop_pct = round((1 - last_avg / first_avg) * 100, 1) if first_avg > 0 else 0
        anomalies.append({
            "type": "тренд_падения",
            "severity": "информационная",
            "date": None,
            "description": (
                f"За период дебит нефти снизился на {drop_pct}% "
                f"(с {first_avg:.0f} до {last_avg:.0f} м³/сут)."
            ),
        })

    summary = (
        "Существенных отклонений от тренда не выявлено."
        if not anomalies else
        f"Выявлено {len(anomalies)} отклонений."
    )
    return {"anomalies": anomalies, "summary": summary}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from tools.get_production_data import get_production_data

    for well, period in [
        ("15/9-F-14", "2014-06"),
        ("15/9-F-12", "2015-06"),
    ]:
        print(f"\n=== {well} / {period} ===")
        prod = get_production_data(well, period, source="volve")
        result = detect_anomalies_volve(prod)
        print(result["summary"])
        for a in result["anomalies"]:
            print(f"  [{a['severity']}] {a['description']}")
