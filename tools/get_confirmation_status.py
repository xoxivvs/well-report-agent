"""
Инструмент 5: get_confirmation_status
Восприятие — чтение статуса подтверждения отчёта инженером.

Проверяет журнал confirmation_log.
Возможные статусы: pending / approved / rejected / not_found
"""

import sqlite3

if __package__ in (None, ""):  # прямой запуск: python tools/get_confirmation_status.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DB_PATH


def register_report(well_id: int, period: str, report_type: str) -> int:
    """
    Вспомогательная функция: регистрирует новый отчёт в report_requests.
    Возвращает report_id.
    """
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO report_requests (well_id, period, report_type, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
    """, (well_id, period, report_type, datetime.now().isoformat()))
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return report_id


def get_confirmation_status(report_id: int) -> dict:
    """
    Возвращает статус подтверждения отчёта.

    Args:
        report_id: ID отчёта из таблицы report_requests

    Returns:
        dict: {
            "status": "success" | "empty" | "error",
            "data": {
                "report_id": int,
                "confirmation_status": "pending" | "approved" | "rejected" | "not_found",
                "timestamp": str | None
            },
            "error": str | None
        }
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Проверяем, существует ли отчёт
        report = cursor.execute("""
            SELECT id, well_id, period, status FROM report_requests WHERE id = ?
        """, (report_id,)).fetchone()

        if report is None:
            conn.close()
            return {
                "status": "error",
                "data": {
                    "report_id": report_id,
                    "confirmation_status": "not_found"
                },
                "error": f"Отчёт с ID={report_id} не зарегистрирован"
            }

        # Читаем последнюю запись из confirmation_log
        log = cursor.execute("""
            SELECT status, timestamp FROM confirmation_log
            WHERE report_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (report_id,)).fetchone()

        conn.close()

        if log is None:
            return {
                "status": "empty",
                "data": {
                    "report_id": report_id,
                    "confirmation_status": "pending",
                    "timestamp": None
                },
                "error": None
            }

        return {
            "status": "success",
            "data": {
                "report_id": report_id,
                "confirmation_status": log["status"],
                "timestamp": log["timestamp"]
            },
            "error": None
        }

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": f"Ошибка БД: {e}"
        }


def confirm_report(report_id: int, decision: str = "approved") -> dict:
    """
    Вспомогательная функция: записывает решение инженера в журнал.
    decision: 'approved' | 'rejected'
    """
    from datetime import datetime
    if decision not in ("approved", "rejected"):
        return {"status": "error", "error": "decision должен быть approved или rejected"}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO confirmation_log (report_id, status, timestamp)
        VALUES (?, ?, ?)
    """, (report_id, decision, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return {"status": "success", "report_id": report_id, "decision": decision}


# --- Локальный тест ---
if __name__ == "__main__":
    # 1. Регистрируем новый отчёт
    rid = register_report(well_id=5, period="2026-09", report_type="monthly")
    print(f"📝 Зарегистрирован отчёт с ID={rid}")

    # 2. Проверяем статус до подтверждения → должно быть pending
    print("\n1) До подтверждения:")
    print(get_confirmation_status(rid))

    # 3. Инженер подтверждает
    confirm_report(rid, "approved")
    print("\n2) После подтверждения:")
    print(get_confirmation_status(rid))

    # 4. Проверяем несуществующий отчёт
    print("\n3) Несуществующий отчёт (ID=99999):")
    print(get_confirmation_status(99999))
