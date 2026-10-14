"""
Список доступных моделей у LLM-провайдера (OpenAI-совместимый API).
Запуск: python scripts/list_models.py
Требует переменную окружения LLM_API_KEY (или .env).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from src.config import LLM_API_KEY, LLM_BASE_URL

if not LLM_API_KEY:
    print("LLM_API_KEY не задан")
    print("Windows:  $env:LLM_API_KEY = '...'")
    print("Linux:    export LLM_API_KEY=...")
    print("Или добавьте строку в .env")
    raise SystemExit(1)

print(f"Ключ найден, длина: {len(LLM_API_KEY)} символов")
print(f"Запрос к {LLM_BASE_URL}/models...\n")

r = requests.get(f"{LLM_BASE_URL}/models",
                 headers={"Authorization": f"Bearer {LLM_API_KEY}"})

if r.status_code != 200:
    print(f"Ошибка {r.status_code}: {r.text[:200]}")
    raise SystemExit(1)

models = [m["id"] for m in r.json().get("data", [])]
print(f"Всего моделей: {len(models)}\n")

keywords = ["gpt-4", "claude", "gemini", "qwen", "deepseek", "llama"]
print("Рекомендуемые модели для кодинга:")
print("-" * 60)
for m in models:
    if any(k in m.lower() for k in keywords):
        print(f"  {m}")
