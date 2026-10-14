"""
Быстрая проверка наполнения БД.
Запуск: python scripts/check_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

from src.config import DB_PATH


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"БД: {DB_PATH}")

    print("\n📊 Скважины:")
    for row in cursor.execute("SELECT * FROM wells LIMIT 5"):
        print(" ", row)

    print("\n📊 Добыча (последние 3 записи):")
    for row in cursor.execute("SELECT * FROM production ORDER BY date DESC LIMIT 3"):
        print(" ", row)

    print("\n📊 Телеметрия (последние 3 записи):")
    for row in cursor.execute("SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT 3"):
        print(" ", row)

    print("\n📊 Геология:")
    for row in cursor.execute("SELECT * FROM geo_reports LIMIT 3"):
        print(" ", row)

    print("\n📊 Общее количество записей:")
    for table in ["wells", "production", "telemetry", "geo_reports", "production_volve"]:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
