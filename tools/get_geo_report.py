"""
Инструмент 4: get_geo_report
Восприятие — парсинг PDF геологического отчёта.

Извлекает:
- пластовое давление
- режим работы
- дату отчёта
"""

import os
import re
import sqlite3

import pdfplumber

if __package__ in (None, ""):  # прямой запуск: python tools/get_geo_report.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pathlib import Path

from src.config import BASE_DIR, DATA_DIR, DB_PATH


def _find_pdf_path(well_id: int, period: str) -> str | None:
    """
    Ищет путь к PDF в таблице geo_reports.
    Возвращает путь, если отчёт есть.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if len(period) == 7:  # YYYY-MM
        pattern = period + "%"
    else:
        pattern = period + "%"

    row = cursor.execute("""
        SELECT pdf_path FROM geo_reports
        WHERE well_id = ? AND date LIKE ?
        ORDER BY date DESC LIMIT 1
    """, (well_id, pattern)).fetchone()

    conn.close()
    if not row or not row[0]:
        return None
    # В БД пути лежат относительные ("data/geo_reports/..."). Приводим к
    # абсолютным: сначала ищем относительно корня проекта, затем —
    # относительно текущего каталога данных (актуально для тестов/облака).
    path = Path(row[0])
    if not path.is_absolute():
        resolved = BASE_DIR / path
        if not resolved.exists():
            alt = DATA_DIR / path
            if alt.exists():
                resolved = alt
        path = resolved
    return str(path)


def _parse_pdf(path: str) -> dict:
    """Извлекает данные из PDF-файла."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF не найден: {path}")

    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    if not text.strip():
        raise ValueError("PDF пустой или не содержит текста")

    # Парсим поля
    pressure_match = re.search(r"Пластовое давление:\s*([\d.]+)", text)
    mode_match = re.search(r"Режим работы:\s*(.+)", text)
    date_match = re.search(r"Дата:\s*([\d-]+)", text)

    if not pressure_match:
        raise ValueError("Не удалось извлечь пластовое давление из PDF")

    return {
        "reservoir_pressure": float(pressure_match.group(1)),
        "mode": mode_match.group(1).strip() if mode_match else "неизвестно",
        "date": date_match.group(1) if date_match else None,
        "pdf_path": path
    }


def get_geo_report(well_id: int, period: str) -> dict:
    """
    Возвращает данные геологического отчёта.

    Returns:
        dict: {
            "status": "success" | "empty" | "error",
            "data": {...},
            "error": str | None
        }
    """
    try:
        path = _find_pdf_path(well_id, period)

        if path is None:
            return {
                "status": "empty",
                "data": {
                    "well_id": well_id,
                    "period": period,
                    "reservoir_pressure": None,
                    "mode": None
                },
                "error": None
            }

        parsed = _parse_pdf(path)

        return {
            "status": "success",
            "data": {
                "well_id": well_id,
                "period": period,
                **parsed
            },
            "error": None
        }

    except FileNotFoundError as e:
        return {
            "status": "error",
            "data": None,
            "error": f"Файл не найден: {e}"
        }
    except ValueError as e:
        return {
            "status": "error",
            "data": None,
            "error": f"Ошибка парсинга PDF: {e}"
        }
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": f"Неожиданная ошибка: {e}"
        }


# --- Локальный тест ---
if __name__ == "__main__":
    tests = [
        (5, "2026-09"),
        (5, "2020-01"),
        (99, "2026-09"),
    ]

    for well_id, period in tests:
        result = get_geo_report(well_id, period)
        print(f"\nСкважина {well_id}, период {period}")
        print(f"Статус: {result['status']}")
        if result["status"] == "success":
            d = result["data"]
            print(f"  Пластовое давление: {d['reservoir_pressure']} атм")
            print(f"  Режим: {d['mode']}")
            print(f"  Дата: {d['date']}")
        else:
            print(f"  Данные: {result['data']}")
            print(f"  Ошибка: {result['error']}")
