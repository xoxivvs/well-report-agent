"""
Вспомогательный инструмент: список сгенерированных отчётов.

Читает report_requests + confirmation_log + data/sent/.
"""

import glob
import os
import sqlite3

if __package__ in (None, ""):  # прямой запуск: python tools/list_reports.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DB_PATH, DRAFTS_DIR, SENT_DIR


def list_reports(limit: int = 20) -> list:
    """
    Возвращает последние N отчётов из журнала.
    Каждый элемент:
        {
            "report_id": int,
            "well_id": int,
            "period": str,
            "report_type": str,
            "status": str,           # pending / approved / rejected / sent
            "created_at": str,
            "pdf_path": str | None,
            "confirmation_status": str | None
        }
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute("""
            SELECT
                r.id AS report_id,
                r.well_id,
                r.period,
                r.report_type,
                r.status,
                r.created_at,
                c.status AS confirmation_status,
                c.timestamp AS confirmation_time
            FROM report_requests r
            LEFT JOIN confirmation_log c
                ON c.report_id = r.id
                AND c.timestamp = (
                    SELECT MAX(timestamp) FROM confirmation_log
                    WHERE report_id = r.id
                )
            ORDER BY r.id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        conn.close()

        result = []
        for row in rows:
            d = dict(row)

            # Ищем PDF по ID
            pdf_pattern = os.path.join(DRAFTS_DIR, f"report_well{d['well_id']}_{d['period']}_*.pdf")
            pdfs = sorted(glob.glob(pdf_pattern))
            d["pdf_path"] = pdfs[-1] if pdfs else None

            # Ищем файл отправки
            sent_pattern = os.path.join(SENT_DIR, f"sent_report_{d['report_id']}_*.txt")
            sents = sorted(glob.glob(sent_pattern))
            d["sent_path"] = sents[-1] if sents else None

            result.append(d)

        return result

    except Exception as e:
        print(f"Ошибка получения списка отчётов: {e}")
        return []


def get_stats() -> dict:
    """Сводная статистика по всем отчётам."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        total = cursor.execute("SELECT COUNT(*) FROM report_requests").fetchone()[0]
        approved = cursor.execute(
            "SELECT COUNT(*) FROM confirmation_log WHERE status = 'approved'"
        ).fetchone()[0]
        rejected = cursor.execute(
            "SELECT COUNT(*) FROM confirmation_log WHERE status = 'rejected'"
        ).fetchone()[0]

        conn.close()

        sent = len(glob.glob(os.path.join(SENT_DIR, "sent_report_*.txt")))
        drafts = len(glob.glob(os.path.join(DRAFTS_DIR, "*.pdf")))

        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "sent": sent,
            "drafts": drafts,
            "approval_rate": round(approved / total * 100, 1) if total > 0 else 0,
        }
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        return {}


if __name__ == "__main__":
    reports = list_reports(limit=10)
    print(f"Найдено отчётов: {len(reports)}")
    for r in reports[:5]:
        print(f"  ID={r['report_id']} | Скв={r['well_id']} | {r['period']} | "
              f"status={r['status']} | conf={r['confirmation_status']}")

    print("\nСтатистика:")
    stats = get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
