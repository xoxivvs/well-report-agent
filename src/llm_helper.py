"""
LLM-помощник для агента отчётности.

Режим по умолчанию — внешний API (OpenAI-совместимый), ключ берётся
из переменной окружения LLM_API_KEY или из Streamlit secrets.

Локальный Ollama включается флагом USE_OLLAMA=true (нужен установленный
пакет ollama и запущенный сервер) — импорт в этом случае ленивый,
чтобы приложение не падало там, где пакет не установлен (облако, CI).
"""

import json
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    LLM_BASE_URL,
    LLM_MODEL,
    OLLAMA_MODEL,
    USE_OLLAMA,
)

# Дефолты дублируем здесь же — config может быть переопределён окружением
DEFAULT_MODEL_API = "openai/gpt-4o-mini"


def _secret(name: str, default: str | None = None) -> str | None:
    """
    Читает секрет по схеме: переменная окружения → Streamlit secrets → default.
    На Streamlit Community Cloud секреты задаются в UI (secrets.toml),
    локально — через .env / переменные окружения.
    """
    val = os.environ.get(name)
    if val:
        return val
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        # st.secrets недоступен (не Streamlit, нет файла secrets и т.п.)
        pass
    return default


# --- Режим работы ---
# Значения читаем через _secret: env → st.secrets → config-дефолт.
# Это позволяет задавать LLM_* как переменные окружения локально и
# как [secrets] на Streamlit Community Cloud.
API_KEY = _secret("LLM_API_KEY")
_MODEL_FROM_SECRET = _secret("LLM_MODEL")
_BASE_URL_FROM_SECRET = _secret("LLM_BASE_URL")

MODEL = OLLAMA_MODEL if USE_OLLAMA else (_MODEL_FROM_SECRET or LLM_MODEL)
BASE_URL = _BASE_URL_FROM_SECRET or LLM_BASE_URL

if USE_OLLAMA:
    try:
        import ollama  # лениво: только в Ollama-режиме
    except ImportError:
        ollama = None
        print("[LLM] USE_OLLAMA=true, но пакет 'ollama' не установлен — "
              "переключаюсь на API-режим")
        USE_OLLAMA = False


# --- Единая точка вызова ---
def _call_llm(prompt: str, system: str = None, temperature: float = 0.2, max_tokens: int = 500) -> str:
    """
    Вызов LLM. Работает и через Ollama, и через OpenAI-совместимый API.
    Возвращает текст ответа или сообщение об ошибке.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        if USE_OLLAMA and ollama is not None:
            response = ollama.chat(
                model=MODEL,
                messages=messages,
                options={"temperature": temperature, "num_predict": max_tokens},
            )
            return response["message"]["content"].strip()

        # API-режим
        if not API_KEY:
            return ("[LLM недоступен] Не задан LLM_API_KEY "
                    "(переменная окружения или Streamlit secrets).")
        import requests
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": MODEL or DEFAULT_MODEL_API,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        r = requests.post(f"{BASE_URL}/chat/completions", json=payload,
                          headers=headers, timeout=120)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return f"Ошибка API: HTTP {r.status_code}"
    except Exception as e:
        return f"Ошибка LLM: {e}"


# --- Парсинг запроса инженера ---
def parse_query_with_llm(query: str, wells: list) -> dict:
    """Извлекает из свободного текста: скважину, период, тип отчёта."""
    wells_str = ", ".join(wells)

    system = ("Ты — ассистент инженера-технолога нефтедобывающего предприятия. "
              "Твоя задача — извлекать параметры запроса и возвращать строгий JSON.")

    prompt = f"""Извлеки из запроса:
1. Название скважины (одно из: {wells_str})
2. Период в формате YYYY-MM
3. Тип отчёта (daily / weekly / monthly)

Запрос: "{query}"

Верни ТОЛЬКО JSON без пояснений:
{{"well_name": "...", "period": "YYYY-MM", "report_type": "monthly"}}
"""

    text = _call_llm(prompt, system=system, temperature=0.1, max_tokens=150)

    try:
        # Убираем markdown-обёртку
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                if "{" in part:
                    text = part.strip()
                    if text.startswith("json"):
                        text = text[4:].strip()
                    break

        # Ищем JSON-подстроку
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        return json.loads(text)
    except Exception as e:
        return {"error": str(e), "raw": text[:200]}


# --- Few-shot интерпретация аномалий ---
INTERPRETATION_SYSTEM = """Ты — инженер-технолог нефтегазовой компании.

Область компетенции: анализ аномалий добычи, диагностика УЭЦН, интерпретация данных телеметрии.

Ограничения:
- Ты анализируешь данные по КОНКРЕТНОЙ действующей скважине за КОНКРЕТНЫЙ период.
- Рекомендации должны касаться её текущей эксплуатации: диагностика УЭЦН,
  оценка забойного давления, ограничение водопритока, PLT, ОПЗ, ППР.
- Не предлагай капитальных решений (бурение новых скважин, разведка, сейсмика) —
  это вне области операционного отчёта и вне твоей компетенции.
- Если данных недостаточно — укажи это, а не выдумывай.

Формат: 3-5 предложений, сухо, технически."""


INTERPRETATION_EXAMPLES = """
Примеры правильной интерпретации:

Аномалия: "26.06.2014: дебит нефти упал до 184 м³/сут — на 60% ниже 14-дневного среднего."
Ответ: Резкое падение дебита на 60% относительно тренда указывает на нарушение режима работы скважины. Наиболее вероятная причина — срыв подачи УЭЦН или кратковременная остановка по технологическим причинам. Требуется диагностика насосного оборудования и оценка забойного давления. При подтверждении срыва подачи — рассмотреть замену УЭЦН или оптимизацию режима.

Аномалия: "Обводнённость выросла с 60% до 88% за 3 месяца."
Ответ: Рост обводнённости на 28 п.п. свидетельствует о прорыве пластовой воды к интервалу перфорации. Это характерно для поздней стадии разработки. Требуется оценка профиля притока (PLT) и рассмотрение изоляции обводнённых интервалов. При сохранении тренда возможна потеря рентабельного дебита нефти.
"""


def generate_interpretation(anomalies: list, well_name: str, period: str) -> str:
    """Генерирует текстовую интерпретацию аномалий."""
    if not anomalies or anomalies == ["Существенных отклонений за отчётный период не выявлено."]:
        return "Существенных отклонений за период не выявлено. Режим работы стабилен."

    anomalies_text = "\n".join(f"- {a}" for a in anomalies)

    prompt = f"""{INTERPRETATION_EXAMPLES}

Теперь проанализируй аномалии по скважине {well_name} за {period}:
{anomalies_text}

Напиши краткую техническую интерпретацию (3-5 предложений)."""

    return _call_llm(prompt, system=INTERPRETATION_SYSTEM, temperature=0.3, max_tokens=400)


def generate_recommendations_llm(anomalies: list, well_name: str, period: str) -> str:
    """Генерирует рекомендации через LLM."""
    if not anomalies:
        return "• [Низкий] Продолжить режим мониторинга."

    anomalies_text = "\n".join(f"- {a}" for a in anomalies)

    system = ("Ты — инженер-технолог. Даёшь только конкретные технические рекомендации. "
              "Формат строго: • [Приоритет] Действие. "
              "Приоритеты: Высокий / Средний / Низкий.")

    prompt = f"""На основе аномалий по действующей скважине {well_name} за {period}:
{anomalies_text}

Дай 2-4 рекомендации. Разрешены только: диагностика УЭЦН, PLT, ОПЗ,
ограничение водопритока, оптимизация режима насоса, ППР, усиление мониторинга.

Запрещено: бурение, разведка, сейсмика.

Только список, без пояснений."""

    text = _call_llm(prompt, system=system, temperature=0.2, max_tokens=300)

    # Фильтруем только строки с •
    lines = [line.strip() for line in text.split("\n") if line.strip().startswith("•")]
    return "\n".join(lines) if lines else text


# --- Тест ---
if __name__ == "__main__":
    wells = ["15/9-F-14", "15/9-F-12", "15/9-F-11", "15/9-F-15 D", "15/9-F-1 C", "15/9-F-5"]

    print("=" * 60)
    print("ТЕСТ 1: Парсинг запроса")
    print("=" * 60)
    test_query = "Сделай подробный отчёт по скважине 15/9-F-14 за июнь 2014"
    result = parse_query_with_llm(test_query, wells)
    print(f"Запрос: {test_query}")
    print(f"Результат: {result}")

    print("\n" + "=" * 60)
    print("ТЕСТ 2: Интерпретация аномалий (few-shot)")
    print("=" * 60)
    anomalies = [
        "2014-06-26: дебит нефти упал до 184 м³/сут — на 60% ниже 14-дневного среднего."
    ]
    interp = generate_interpretation(anomalies, "15/9-F-14", "2014-06")
    print(interp)

    print("\n" + "=" * 60)
    print("ТЕСТ 3: Рекомендации")
    print("=" * 60)
    recs = generate_recommendations_llm(anomalies, "15/9-F-14", "2014-06")
    print(recs)
