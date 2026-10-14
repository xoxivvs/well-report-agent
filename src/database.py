import sqlite3

if __package__ in (None, ""):  # прямой запуск: python src/database.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, DB_PATH


def create_database():
    """Создаёт SQLite-БД со всеми таблицами."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)  # первый запуск / чистый клон
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Скважины
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wells (
            well_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            field TEXT,
            status TEXT DEFAULT 'active'
        )
    """)

    # 2. Добыча
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            well_id INTEGER,
            date TEXT,
            liquid_rate REAL,
            oil_rate REAL,
            water_cut REAL,
            FOREIGN KEY (well_id) REFERENCES wells(well_id)
        )
    """)

    # 3. Телеметрия
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            well_id INTEGER,
            timestamp TEXT,
            runtime_hours REAL,
            alarm_code TEXT,
            FOREIGN KEY (well_id) REFERENCES wells(well_id)
        )
    """)

    # 4. Геологические отчёты
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geo_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            well_id INTEGER,
            date TEXT,
            reservoir_pressure REAL,
            mode TEXT,
            pdf_path TEXT,
            FOREIGN KEY (well_id) REFERENCES wells(well_id)
        )
    """)

    # 5. Журнал запросов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS report_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            well_id INTEGER,
            period TEXT,
            report_type TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    # 6. Журнал подтверждений
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS confirmation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            status TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ База данных создана:", DB_PATH)


if __name__ == "__main__":
    create_database()
