"""
Интерактивный запуск агента подготовки отчётности.

Режимы:
- auto:    автоматически подтверждает и отправляет (для теста)
- manual:  спрашивает подтверждение у пользователя в терминале
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # корень проекта

from src.agent_graph import build_agent
from src.agent_state import AgentState
from tools.get_confirmation_status import confirm_report
from tools.send_report import send_report


def initial_state(query: str, recipient: str = "boss@company.ru") -> AgentState:
    return {
        "query": query,
        "well_id": None,
        "period": None,
        "report_type": None,
        "production": None,
        "telemetry": None,
        "geo": None,
        "report_id": None,
        "pdf_path": None,
        "anomalies": None,
        "recommendations": None,
        "confirmation_status": None,
        "recipient": recipient,
        "sent": False,
        "error": None,
        "step_count": 0,
    }


def run_auto(query: str):
    """Автоматический режим: подтверждает и отправляет сам (для теста)."""
    print("=" * 60)
    print("РЕЖИМ: АВТОМАТИЧЕСКИЙ (для теста)")
    print("=" * 60)

    agent = build_agent()
    state = agent.invoke(initial_state(query))

    if state.get("error"):
        print(f"\n❌ Ошибка на этапе агента: {state['error']}")
        return

    # Автоматически подтверждаем
    print(f"\n→ Автоматическое подтверждение отчёта ID={state['report_id']}...")
    confirm_report(state["report_id"], "approved")

    # Отправляем
    print(f"→ Отправка на {state['recipient']}...")
    send_result = send_report(state["report_id"], state["pdf_path"], state["recipient"])

    print("\n" + "=" * 60)
    print("ИТОГ:")
    print("=" * 60)
    if send_result["status"] == "success":
        print(f"✅ Отчёт отправлен: {send_result['data']['sent_path']}")
    else:
        print(f"❌ Ошибка отправки: {send_result['error']}")
    print(f"PDF: {state['pdf_path']}")
    print(f"Аномалии: {state['anomalies']}")
    print(f"Рекомендации: {state['recommendations']}")


def run_manual(query: str):
    """Интерактивный режим: человек подтверждает в терминале."""
    print("=" * 60)
    print("РЕЖИМ: ИНТЕРАКТИВНЫЙ (человек подтверждает)")
    print("=" * 60)

    agent = build_agent()
    state = agent.invoke(initial_state(query))

    if state.get("error"):
        print(f"\n❌ Ошибка на этапе агента: {state['error']}")
        return

    print("\n" + "=" * 60)
    print("ЧЕРНОВИК ГОТОВ, ТРЕБУЕТСЯ ПРОВЕРКА")
    print("=" * 60)
    print(f"Скважина:      {state['well_id']}")
    print(f"Период:        {state['period']}")
    print(f"PDF:           {state['pdf_path']}")
    print(f"Аномалии:      {state['anomalies']}")
    print(f"Рекомендации:  {state['recommendations']}")
    print("=" * 60)

    answer = input("\nПодтвердить и отправить отчёт? (да/нет): ").strip().lower()

    if answer in ("да", "д", "yes", "y"):
        confirm_report(state["report_id"], "approved")
        print(f"✅ Отчёт ID={state['report_id']} подтверждён")

        send_result = send_report(state["report_id"], state["pdf_path"], state["recipient"])
        if send_result["status"] == "success":
            print(f"📤 Отчёт отправлен: {send_result['data']['sent_path']}")
        else:
            print(f"❌ Ошибка отправки: {send_result['error']}")
    else:
        confirm_report(state["report_id"], "rejected")
        print("❌ Отчёт отклонён. Отправка не выполнена.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto",
                        help="auto — авто-подтверждение, manual — интерактив")
    parser.add_argument("--query", default="Сделай отчёт по скважине 5 за сентябрь 2026",
                        help="текст запроса")
    args = parser.parse_args()

    if args.mode == "auto":
        run_auto(args.query)
    else:
        run_manual(args.query)
