"""
Генератор PDF-заглушек с поддержкой кириллицы.
"""

import os
import sqlite3

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

if __package__ in (None, ""):  # прямой запуск: python src/generate_pdf_reports.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DB_PATH
from src.config import GEO_REPORTS_DIR as PDF_DIR
from src.fonts import register_fonts

# Кроссплатформенный шрифт с поддержкой кириллицы
FONT_NAME, _FONT_BOLD = register_fonts()


def create_pdf(well_id: int, date: str, pressure: float, mode: str, path: str):
    """Создаёт один PDF-отчёт."""
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    c.setFont(FONT_NAME, 16)
    c.drawString(2 * cm, height - 2 * cm, f"Геологический отчёт по скважине №{well_id}")

    c.setFont(FONT_NAME, 12)
    c.drawString(2 * cm, height - 3.5 * cm, f"Дата: {date}")
    c.drawString(2 * cm, height - 4.5 * cm, f"Пластовое давление: {pressure} атм")
    c.drawString(2 * cm, height - 5.5 * cm, f"Режим работы: {mode}")
    c.drawString(2 * cm, height - 6.5 * cm, "Рекомендации: наблюдение")

    c.save()


def main():
    os.makedirs(PDF_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT well_id, date, reservoir_pressure, mode, pdf_path
        FROM geo_reports
    """).fetchall()
    conn.close()

    for well_id, date, pressure, mode, pdf_path in rows:
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        create_pdf(well_id, date, pressure, mode, pdf_path)

    print(f"✅ Пересоздано {len(rows)} PDF-отчётов с поддержкой кириллицы")


if __name__ == "__main__":
    main()
