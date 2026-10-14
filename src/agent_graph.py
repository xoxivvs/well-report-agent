"""
Агент подготовки отчётности — граф состояний на LangGraph.
Версия 0.3: с замерами времени.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # корень проекта

from langgraph.graph import END, StateGraph

from src.agent_state import AgentState
from tools.generate_report_draft import generate_report_draft
from tools.get_confirmation_status import get_confirmation_status, register_report
from tools.get_geo_report import get_geo_report
from tools.get_production_data import get_production_data
from tools.get_report_request import get_report_request
from tools.get_telemetry import get_telemetry
from tools.send_report import send_report

# --- Узлы графа ---

def node_parse_request(state: AgentState) -> AgentState:
    """Шаг 1: разбор запроса инженера."""
    t0 = time.time()
    print("→ [1] Разбор запроса...")
    result = get_report_request(state["query"])
    elapsed = round(time.time() - t0, 3)

    if result["status"] != "success":
        return {
            **state,
            "error": result["error"],
            "step_count": state["step_count"] + 1,
            "time_parse": elapsed,
        }

    return {
        **state,
        "well_id": result["data"]["well_id"],
        "period": result["data"]["period"],
        "report_type": result["data"]["report_type"],
        "step_count": state["step_count"] + 1,
        "time_parse": elapsed,
    }


def node_collect_data(state: AgentState) -> AgentState:
    """Шаг 2: сбор данных из трёх источников."""
    t0 = time.time()
    print("→ [2] Сбор данных (добыча, телеметрия, геология)...")

    prod = get_production_data(state["well_id"], state["period"])
    tel = get_telemetry(state["well_id"], state["period"])
    geo = get_geo_report(state["well_id"], state["period"])
    elapsed = round(time.time() - t0, 3)

    error = None
    if prod["status"] == "error":
        error = prod["error"]
    elif tel["status"] == "error":
        error = tel["error"]
    elif geo["status"] == "error":
        error = geo["error"]

    return {
        **state,
        "production": prod,
        "telemetry": tel,
        "geo": geo,
        "error": error,
        "step_count": state["step_count"] + 1,
        "time_collect": elapsed,
    }


def node_generate_draft(state: AgentState) -> AgentState:
    """Шаг 3: генерация черновика PDF."""
    t0 = time.time()
    print("→ [3] Генерация PDF-черновика...")

    result = generate_report_draft(
        state["well_id"], state["period"],
        state["production"], state["telemetry"], state["geo"]
    )

    if result["status"] != "success":
        return {
            **state,
            "error": result["error"],
            "step_count": state["step_count"] + 1,
            "time_draft": round(time.time() - t0, 3),
        }

    rid = register_report(state["well_id"], state["period"], state["report_type"])
    elapsed = round(time.time() - t0, 3)

    return {
        **state,
        "report_id": rid,
        "pdf_path": result["data"]["pdf_path"],
        "anomalies": result["data"]["anomalies"],
        "recommendations": result["data"]["recommendations"],
        "step_count": state["step_count"] + 1,
        "time_draft": elapsed,
    }


def node_check_confirmation(state: AgentState) -> AgentState:
    """Шаг 4: проверка статуса подтверждения."""
    t0 = time.time()
    print("→ [4] Проверка подтверждения...")

    result = get_confirmation_status(state["report_id"])
    status = result["data"]["confirmation_status"] if result["data"] else "not_found"
    elapsed = round(time.time() - t0, 3)

    return {
        **state,
        "confirmation_status": status,
        "step_count": state["step_count"] + 1,
        "time_confirm": elapsed,
    }


def node_send(state: AgentState) -> AgentState:
    """Шаг 5: отправка отчёта."""
    print("→ [5] Отправка отчёта...")

    if state["confirmation_status"] != "approved":
        return {
            **state,
            "error": f"Нельзя отправить: статус {state['confirmation_status']}",
            "step_count": state["step_count"] + 1,
        }

    recipient = state.get("recipient") or "boss@company.ru"
    result = send_report(state["report_id"], state["pdf_path"], recipient)

    if result["status"] != "success":
        return {**state, "error": result["error"], "step_count": state["step_count"] + 1}

    return {
        **state,
        "sent": True,
        "recipient": recipient,
        "step_count": state["step_count"] + 1,
    }


# --- Условия переходов ---

def check_after_parse(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    return "collect"


def check_after_collect(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    return "draft"


def check_after_confirmation(state: AgentState) -> str:
    if state["confirmation_status"] == "approved":
        return "send"
    return "end"


# --- Сборка графа ---

def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("parse", node_parse_request)
    graph.add_node("collect", node_collect_data)
    graph.add_node("draft", node_generate_draft)
    graph.add_node("confirm", node_check_confirmation)
    graph.add_node("send", node_send)

    graph.set_entry_point("parse")

    graph.add_conditional_edges("parse", check_after_parse, {"collect": "collect", "end": END})
    graph.add_conditional_edges("collect", check_after_collect, {"draft": "draft", "end": END})
    graph.add_edge("draft", "confirm")
    graph.add_conditional_edges("confirm", check_after_confirmation, {"send": "send", "end": END})
    graph.add_edge("send", END)

    return graph.compile()


def run_agent_with_timing(query: str, recipient: str = "boss@company.ru") -> dict:
    """
    Обёртка: запускает агента и считает общее время.
    Возвращает финальное состояние + время.
    """
    agent = build_agent()

    initial: AgentState = {
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
        "time_parse": None,
        "time_collect": None,
        "time_draft": None,
        "time_confirm": None,
        "time_total": None,
    }

    t0 = time.time()
    final_state = agent.invoke(initial)
    total = round(time.time() - t0, 3)

    final_state["time_total"] = total
    return final_state


# --- Тестовый запуск ---

if __name__ == "__main__":
    result = run_agent_with_timing("Сделай отчёт по скважине 5 за сентябрь 2026")

    print("\n" + "=" * 50)
    print("РЕЗУЛЬТАТ + МЕТРИКИ ВРЕМЕНИ:")
    print("=" * 50)
    print(f"Скважина:        {result.get('well_id')}")
    print(f"Период:          {result.get('period')}")
    print(f"PDF:             {result.get('pdf_path')}")
    print(f"Подтверждение:   {result.get('confirmation_status')}")
    print(f"Шагов:           {result.get('step_count')}")
    print()
    print("⏱ Время по шагам (секунды):")
    print(f"  [1] Разбор запроса:       {result.get('time_parse')}")
    print(f"  [2] Сбор данных:          {result.get('time_collect')}")
    print(f"  [3] Генерация PDF:        {result.get('time_draft')}")
    print(f"  [4] Проверка подтвержд.:  {result.get('time_confirm')}")
    print("  ─────────────────────────")
    print(f"  ИТОГО:                    {result.get('time_total')}")
    print()
    print("💰 Экономия vs ручная работа (4 часа = 14400 сек):")
    saved = 14400 - result.get('time_total', 0)
    print(f"  Сэкономлено:              {saved:.1f} сек ({saved/3600:.2f} ч)")
    print(f"  Ускорение:                {14400 / result.get('time_total', 1):.0f}x")
