"""
Проверка данных Volve за конкретный месяц по скважине.
Запуск: python scripts/check_2008.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

from src.config import DB_PATH

WELL_NAME = "15/9-F-14"
PERIOD = "2008-06"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

row = cur.execute(
    """
    SELECT COUNT(*), SUM(on_stream_hours)
    FROM production_volve
    WHERE well_name = ? AND date LIKE ?
    """,
    (WELL_NAME, PERIOD + "%"),
).fetchone()

print(f"Записей за {PERIOD}: {row[0]}, сумма часов: {row[1]}")

print("\nПервые 10 записей:")
for r in cur.execute(
    """
    SELECT date, on_stream_hours, oil_volume, water_cut
    FROM production_volve
    WHERE well_name = ? AND date LIKE ?
    ORDER BY date LIMIT 10
    """,
    (WELL_NAME, PERIOD + "%"),
):
    print(f"  {r[0]} | hours={r[1]} | oil={r[2]} | water_cut={r[3]}")

print("\nВсе доступные месяцы:")
for r in cur.execute(
    """
    SELECT DISTINCT substr(date, 1, 7) AS month
    FROM production_volve
    WHERE well_name = ?
    ORDER BY month
    """,
    (WELL_NAME,),
):
    print(f"  {r[0]}")

conn.close()
