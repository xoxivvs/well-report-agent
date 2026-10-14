"""
Загрузка реальных данных Volve в SQLite.
Создаёт таблицу production_volve с данными по 7 добывающим скважинам.
"""

import os
import sqlite3

import pandas as pd

if __package__ in (None, ""):  # прямой запуск: python src/load_volve_data.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DB_PATH, RAW_DIR


def find_volve_file():
    """Ищет Excel-файл Volve в data/raw."""
    if not os.path.exists(RAW_DIR):
        raise FileNotFoundError(f"Папка {RAW_DIR} не найдена. Создай её и положи Excel-файл Volve.")

    for f in os.listdir(RAW_DIR):
        if "volve" in f.lower() and f.endswith((".xlsx", ".xls")):
            return os.path.join(RAW_DIR, f)

    raise FileNotFoundError(
        f"Не найден файл Volve в {RAW_DIR}. "
        f"Положи туда 'Volve production data.xlsx'."
    )


def load_volve(file_path):
    """Читает и подготавливает данные Volve."""
    print(f"📖 Читаю: {file_path}")
    df = pd.read_excel(file_path)
    print(f"📊 Исходная таблица: {df.shape[0]} строк × {df.shape[1]} столбцов")

    # Оставляем только добывающие скважины
    if "WELL_TYPE" in df.columns:
        print(f"Типы скважин: {df['WELL_TYPE'].unique().tolist()}")
        df = df[df["WELL_TYPE"] == "OP"].copy()
        print(f"📊 После фильтра OP: {df.shape[0]} строк")

    # Преобразуем дату
    df["DATEPRD"] = pd.to_datetime(df["DATEPRD"], errors="coerce")
    df = df.dropna(subset=["DATEPRD"])

    # Считаем обводнённость
    df["WATER_CUT"] = 0.0
    total_liquid = df["BORE_OIL_VOL"] + df["BORE_WAT_VOL"]
    mask = total_liquid > 0
    df.loc[mask, "WATER_CUT"] = (
        df.loc[mask, "BORE_WAT_VOL"] / total_liquid[mask] * 100
    ).round(2)

    # Приводим к нужным колонкам
    result = pd.DataFrame({
        "well_name": df["NPD_WELL_BORE_NAME"].astype(str),
        "field_name": df["NPD_FIELD_NAME"].astype(str),
        "date": df["DATEPRD"].dt.strftime("%Y-%m-%d"),
        "on_stream_hours": df["ON_STREAM_HRS"].round(2),
        "oil_volume": df["BORE_OIL_VOL"].round(2),
        "gas_volume": df["BORE_GAS_VOL"].round(2),
        "water_volume": df["BORE_WAT_VOL"].round(2),
        "water_cut": df["WATER_CUT"],
        "downhole_pressure": df["AVG_DOWNHOLE_PRESSURE"].round(2),
        "downhole_temperature": df["AVG_DOWNHOLE_TEMPERATURE"].round(2),
        "wellhead_pressure": df["AVG_WHP_P"].round(2),
        "wellhead_temperature": df["AVG_WHT_P"].round(2),
        "choke_size": df["AVG_CHOKE_SIZE_P"].round(2),
    })

    return result


def save_to_sqlite(df):
    """Сохраняет в SQLite в таблицу production_volve."""
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("production_volve", conn, if_exists="replace", index=False)
    conn.close()
    print(f"✅ Данные записаны в таблицу 'production_volve' в {DB_PATH}")


def summary():
    """Показывает сводку по загруженным данным."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total = cursor.execute("SELECT COUNT(*) FROM production_volve").fetchone()[0]
    wells = cursor.execute("SELECT COUNT(DISTINCT well_name) FROM production_volve").fetchone()[0]
    date_min = cursor.execute("SELECT MIN(date) FROM production_volve").fetchone()[0]
    date_max = cursor.execute("SELECT MAX(date) FROM production_volve").fetchone()[0]

    print("\n" + "=" * 50)
    print("СВОДКА ПО ДАННЫМ VOLVE:")
    print("=" * 50)
    print(f"Всего записей:      {total}")
    print(f"Уникальных скважин: {wells}")
    print(f"Период:             {date_min} → {date_max}")

    print("\nТоп-5 скважин по количеству записей:")
    for row in cursor.execute("""
        SELECT well_name, COUNT(*) as cnt
        FROM production_volve
        GROUP BY well_name
        ORDER BY cnt DESC
        LIMIT 5
    """):
        print(f"  {row[0]}: {row[1]} записей")

    print("\nПример записи:")
    columns = [desc[0] for desc in cursor.execute("SELECT * FROM production_volve LIMIT 1").description]
    sample = cursor.execute("SELECT * FROM production_volve LIMIT 1").fetchone()
    for col, val in zip(columns, sample):
     print(f"  {col}: {val}")


if __name__ == "__main__":
    file_path = find_volve_file()
    df = load_volve(file_path)
    save_to_sqlite(df)
    summary()
