"""
Статистика и графики по реальным данным Volve.
Запуск: python scripts/check_volve.py
Графики сохраняются в data/charts/.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import CHARTS_DIR, DB_PATH
from src.fonts import register_fonts

register_fonts()  # кроссплатформенный шрифт для matplotlib


def load_well_data(well_name: str) -> pd.DataFrame:
    """Загружает данные по скважине."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT date, on_stream_hours, oil_volume, gas_volume, water_volume,
               water_cut, downhole_pressure, wellhead_pressure, choke_size
        FROM production_volve
        WHERE well_name = ?
        ORDER BY date
        """,
        conn, params=(well_name,),
    )
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


def stats_by_well() -> pd.DataFrame:
    """Сводная статистика по всем скважинам."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT
            well_name,
            COUNT(*) AS total_days,
            SUM(CASE WHEN on_stream_hours > 0 THEN 1 ELSE 0 END) AS working_days,
            ROUND(AVG(CASE WHEN on_stream_hours > 0 THEN oil_volume END), 2) AS avg_oil,
            ROUND(AVG(CASE WHEN on_stream_hours > 0 THEN water_cut END), 2) AS avg_water_cut,
            ROUND(SUM(oil_volume), 0) AS total_oil,
            ROUND(AVG(CASE WHEN on_stream_hours > 0 THEN wellhead_pressure END), 2) AS avg_whp,
            MIN(date) AS first_date,
            MAX(date) AS last_date
        FROM production_volve
        GROUP BY well_name
        ORDER BY total_days DESC
        """,
        conn,
    )
    conn.close()
    return df


def plot_well(well_name: str) -> None:
    """Строит график дебита, обводнённости и давления."""
    df = load_well_data(well_name)
    df = df[df["on_stream_hours"] > 0]  # только рабочие дни

    if df.empty:
        print(f"⚠ Нет рабочих дней для {well_name}")
        return

    os.makedirs(CHARTS_DIR, exist_ok=True)
    safe_name = well_name.replace("/", "_").replace(" ", "_")
    chart_path = os.path.join(CHARTS_DIR, f"volve_{safe_name}.png")

    fig, ax1 = plt.subplots(figsize=(12, 5))

    ax1.plot(df["date"], df["oil_volume"], color="#2F4F4F", linewidth=1.2,
             label="Дебит нефти, м³/сут")
    ax1.set_xlabel("Дата")
    ax1.set_ylabel("Дебит нефти, м³/сут", color="#2F4F4F")
    ax1.tick_params(axis="y", labelcolor="#2F4F4F")
    ax1.grid(True, linestyle="--", alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(df["date"], df["water_cut"], color="#FFA500",
             linewidth=1.0, linestyle="--", label="Обводнённость, %")
    ax2.set_ylabel("Обводнённость, %", color="#FFA500")
    ax2.tick_params(axis="y", labelcolor="#FFA500")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    plt.title(
        f"Реальная добыча — {well_name} "
        f"({df['date'].min().date()} — {df['date'].max().date()})",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(chart_path, dpi=120, bbox_inches="tight")
    plt.close()

    print(f"📊 График сохранён: {chart_path}")
    print(f"\n  Рабочих дней:              {len(df)}")
    print(f"  Средний дебит нефти:        {df['oil_volume'].mean():.2f} м³/сут")
    print(f"  Максимальный дебит нефти:   {df['oil_volume'].max():.2f} м³/сут")
    print(f"  Средняя обводнённость:      {df['water_cut'].mean():.2f}%")
    print(f"  Максимальная обводнённость: {df['water_cut'].max():.2f}%")


if __name__ == "__main__":
    print("=" * 70)
    print("СТАТИСТИКА ПО РЕАЛЬНЫМ ДАННЫМ VOLVE (только рабочие дни)")
    print("=" * 70)

    stats = stats_by_well()
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print(stats.to_string(index=False))

    print("\n" + "=" * 70)
    print("ГРАФИКИ ПО СКВАЖИНАМ")
    print("=" * 70)

    top_wells = stats.head(3)["well_name"].tolist()
    for well in top_wells:
        print(f"\n--- {well} ---")
        plot_well(well)

    print("\n✅ Готово. Графики в data/charts/")
