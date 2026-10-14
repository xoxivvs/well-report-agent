"""
Вспомогательный инструмент: список доступных скважин и периодов.
Поддерживает Volve (реальные данные) и синтетику.
"""

import sqlite3

if __package__ in (None, ""):  # прямой запуск: python tools/list_wells.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DB_PATH


def list_volve_wells():
    """Список реальных скважин Volve."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT well_name, COUNT(*) AS cnt,
                   MIN(date) AS first_date, MAX(date) AS last_date
            FROM production_volve
            GROUP BY well_name
            ORDER BY cnt DESC
        """).fetchall()
        conn.close()
        return [
            {
                "well_name": r[0],
                "records": r[1],
                "first_date": r[2],
                "last_date": r[3],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Ошибка list_volve_wells: {e}")
        return []


def list_volve_periods(well_name):
    """Доступные периоды (YYYY-MM) для скважины Volve."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT DISTINCT substr(date, 1, 7) AS period
            FROM production_volve
            WHERE well_name = ?
              AND on_stream_hours > 0
            ORDER BY period DESC
        """, (well_name,)).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"Ошибка list_volve_periods: {e}")
        return []


def list_synthetic_wells():
    """Старый список синтетических скважин (для совместимости)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT well_id, name, field FROM wells ORDER BY well_id
        """).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Ошибка list_synthetic_wells: {e}")
        return []


def list_periods(well_id):
    """Периоды для синтетической скважины."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT DISTINCT substr(date, 1, 7) AS period
            FROM production
            WHERE well_id = ?
            ORDER BY period DESC
        """, (well_id,)).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"Ошибка list_periods: {e}")
        return []


# Совместимость со старым app.py
def list_wells():
    return list_synthetic_wells()


if __name__ == "__main__":
    print("=== Volve скважины ===")
    for w in list_volve_wells():
        print(f"  {w['well_name']}: {w['records']} записей, {w['first_date']} → {w['last_date']}")

    if list_volve_wells():
        first = list_volve_wells()[0]["well_name"]
        print(f"\n=== Периоды для {first} (последние 10) ===")
        for p in list_volve_periods(first)[:10]:
            print(f"  {p}")
