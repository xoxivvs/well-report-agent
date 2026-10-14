import random
import sqlite3
from datetime import datetime, timedelta

from faker import Faker

if __package__ in (None, ""):  # прямой запуск: python src/seed_data.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DB_PATH

fake = Faker("ru_RU")


def seed_wells(conn, count=10):
    """Создаёт N скважин."""
    cursor = conn.cursor()
    for i in range(1, count + 1):
        cursor.execute(
            "INSERT OR IGNORE INTO wells (well_id, name, field, status) VALUES (?, ?, ?, ?)",
            (i, f"Скв-{i:03d}", f"Месторождение-{random.choice(['А', 'Б', 'В'])}", "active")
        )
    conn.commit()
    print(f"✅ Добавлено {count} скважин")


def seed_production(conn, days=90):
    """Добыча за последние N дней по каждой скважине."""
    cursor = conn.cursor()
    wells = [row[0] for row in cursor.execute("SELECT well_id FROM wells").fetchall()]
    today = datetime.now()

    for well_id in wells:
        base_oil = random.uniform(30, 150)
        base_water = random.uniform(10, 60)

        for day in range(days):
            date = (today - timedelta(days=day)).strftime("%Y-%m-%d")
            oil_rate = round(base_oil + random.uniform(-10, 10), 2)
            water_cut = round(min(95, max(5, base_water + random.uniform(-5, 5))), 2)
            liquid_rate = round(oil_rate / (1 - water_cut / 100), 2)

            cursor.execute(
                "INSERT INTO production (well_id, date, liquid_rate, oil_rate, water_cut) VALUES (?, ?, ?, ?, ?)",
                (well_id, date, liquid_rate, oil_rate, water_cut)
            )
    conn.commit()
    print(f"✅ Добавлена добыча за {days} дней")


def seed_telemetry(conn, days=90):
    """Телеметрия УЭЦН."""
    cursor = conn.cursor()
    wells = [row[0] for row in cursor.execute("SELECT well_id FROM wells").fetchall()]
    today = datetime.now()

    for well_id in wells:
        runtime = random.uniform(100, 8000)
        for day in range(days):
            ts = (today - timedelta(days=day)).strftime("%Y-%m-%d %H:%M:%S")
            runtime += random.uniform(20, 24)
            alarm = None
            if random.random() < 0.05:
                alarm = random.choice(["OVERHEAT", "OVERLOAD", "LOW_PRESSURE"])

            cursor.execute(
                "INSERT INTO telemetry (well_id, timestamp, runtime_hours, alarm_code) VALUES (?, ?, ?, ?)",
                (well_id, ts, round(runtime, 2), alarm)
            )
    conn.commit()
    print(f"✅ Добавлена телеметрия за {days} дней")


def seed_geo_reports(conn, count_per_well=3):
    """Геологические отчёты."""
    cursor = conn.cursor()
    wells = [row[0] for row in cursor.execute("SELECT well_id FROM wells").fetchall()]
    today = datetime.now()

    for well_id in wells:
        for i in range(count_per_well):
            date = (today - timedelta(days=30 * i)).strftime("%Y-%m-%d")
            pressure = round(random.uniform(150, 250), 2)
            mode = random.choice(["стабильный", "падающий", "восстановление"])
            pdf_path = f"data/geo_reports/well_{well_id}_{date}.pdf"

            cursor.execute(
                "INSERT INTO geo_reports (well_id, date, reservoir_pressure, mode, pdf_path) VALUES (?, ?, ?, ?, ?)",
                (well_id, date, pressure, mode, pdf_path)
            )
    conn.commit()
    print("✅ Добавлены геологические отчёты")


def main():
    conn = sqlite3.connect(DB_PATH)
    seed_wells(conn, count=10)
    seed_production(conn, days=90)
    seed_telemetry(conn, days=90)
    seed_geo_reports(conn, count_per_well=3)
    conn.close()
    print("🎉 База заполнена синтетическими данными")


if __name__ == "__main__":
    main()
