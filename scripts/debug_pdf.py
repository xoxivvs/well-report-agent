"""
Отладка парсинга PDF геологического отчёта.
Запуск: python scripts/debug_pdf.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

import pdfplumber

from src.config import DB_PATH

WELL_ID = 5
PERIOD = "2026-09"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
row = cursor.execute(
    """
    SELECT pdf_path FROM geo_reports
    WHERE well_id = ? AND date LIKE ?
    LIMIT 1
    """,
    (WELL_ID, PERIOD + "%"),
).fetchone()
conn.close()

if not row:
    print(f"❌ Не нашёл PDF-файл для скважины {WELL_ID} в {PERIOD}")
    raise SystemExit(1)

path = Path(row[0])
if not path.is_absolute():
    path = Path(__file__).resolve().parent.parent / path

print(f"📄 Путь: {path}")
print(f"📄 Существует: {path.exists()}")
print("\n--- ТЕКСТ ИЗ PDF ---")
with pdfplumber.open(path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"\n[Страница {i + 1}]")
        print(repr(page.extract_text()))
print("--- КОНЕЦ ТЕКСТА ---")
