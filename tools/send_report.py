"""
Инструмент 7: send_report
Действие (необратимое) — отправка отчёта адресату.

⚠️ Требует подтверждения инженера (approve в confirmation_log).
Без подтверждения отправка не выполняется.

Здесь реализован через запись в лог «отправленных» отчётов.
В реальном продакшене — почтовый сервис / СЭД.
"""

import os
import sqlite3
from datetime import datetime

if __package__ in (None, ""):  # прямой запуск: python tools/send_report.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DB_PATH, SENT_DIR


def _ensure_sent_dir():
    os.makedirs(SENT_DIR, exist_ok=True)


def _is_approved(report_id: int) -> bool:
    """Проверяет, что инженер подтвердил отчёт."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    row = cursor.execute("""
        SELECT status FROM confirmation_log
        WHERE report_id = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (report_id,)).fetchone()
    conn.close()
    return row is not None and row[0] == "approved"


def _mark_sent(report_id: int, recipient: str) -> str:
    """Регистрирует отправку в журнале и возвращает путь к копии."""
    _ensure_sent_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sent_path = os.path.join(SENT_DIR, f"sent_report_{report_id}_{timestamp}.txt")

    with open(sent_path, "w", encoding="utf-8") as f:
        f.write(f"Отчёт ID={report_id}\n")
        f.write(f"Адресат: {recipient}\n")
        f.write(f"Дата отправки: {datetime.now().isoformat()}\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE report_requests SET status = 'sent' WHERE id = ?
    """, (report_id,))
    conn.commit()
    conn.close()

    return sent_path


def send_report(report_id: int, pdf_path: str, recipient: str) -> dict:
    """
    Отправляет отчёт адресату (имитация).

    Args:
        report_id: ID отчёта
        pdf_path: путь к PDF-черновику
        recipient: email/СЭД-адрес

    Returns:
        dict: {
            "status": "success" | "error",
            "data": {"sent_path": str, "recipient": str},
            "error": str | None
        }
    """
    # 1. Проверка: PDF существует
    if not os.path.exists(pdf_path):
        return {
            "status": "error",
            "data": None,
            "error": f"PDF не найден: {pdf_path}"
        }

    # 2. Проверка: отчёт подтверждён инженером
    if not _is_approved(report_id):
        return {
            "status": "error",
            "data": None,
            "error": "Отчёт не подтверждён инженером (требуется approved)"
        }

    # 3. Проверка: адресат указан
    if not recipient or "@" not in recipient:
        return {
            "status": "error",
            "data": None,
            "error": "Некорректный адресат (нужен email)"
        }

    # 4. Имитация отправки
    try:
        sent_path = _mark_sent(report_id, recipient)
        return {
            "status": "success",
            "data": {
                "sent_path": sent_path,
                "recipient": recipient,
                "pdf_path": pdf_path,
                "sent_at": datetime.now().isoformat()
            },
            "error": None
        }
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": f"Ошибка отправки: {e}"
        }


# --- Локальный тест ---
if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from tools.get_confirmation_status import confirm_report, register_report

    # 1. Регистрируем отчёт
    rid = register_report(5, "2026-09", "monthly")
    print(f"Зарегистрирован отчёт ID={rid}")

    # 2. Пытаемся отправить БЕЗ подтверждения — должно упасть
    print("\n1) Без подтверждения:")
    print(send_report(rid, "data/drafts/fake.pdf", "boss@company.ru"))

    # 3. Подтверждаем инженером
    confirm_report(rid, "approved")

    # 4. Отправляем с существующим PDF (замени на реальный путь из предыдущего шага)
    import glob
    pdfs = glob.glob("data/drafts/*.pdf")
    if pdfs:
        real_pdf = pdfs[0]
        print(f"\n2) С подтверждением, PDF={real_pdf}:")
        print(send_report(rid, real_pdf, "boss@company.ru"))

    # 5. Некорректный адресат
    print("\n3) Некорректный адресат:")
    print(send_report(rid, pdfs[0] if pdfs else "fake.pdf", "not-an-email"))
