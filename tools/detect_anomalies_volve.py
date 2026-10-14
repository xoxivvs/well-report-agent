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
