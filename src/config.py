"""
Центральная конфигурация проекта: пути, настройки окружения.

Единственная точка правды для путей — все модули импортируют отсюда,
а не собирают пути из строки "data/..." вручную (это ломалось при
запуске не из корня репозитория).
"""

import os
from pathlib import Path

# Загружаем .env локально (в облаке переменные приходят из настроек/секретов).
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# --- Пути ---
# Корень проекта = родитель каталога src/ (работает из любого CWD)
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.environ.get("WELL_REPORT_DATA_DIR", BASE_DIR / "data"))

DB_PATH = str(DATA_DIR / "wells.db")
GEO_REPORTS_DIR = str(DATA_DIR / "geo_reports")
DRAFTS_DIR = str(DATA_DIR / "drafts")
CHARTS_DIR = str(DATA_DIR / "charts")
SENT_DIR = str(DATA_DIR / "sent")
EXCEL_DIR = str(DATA_DIR / "excel")
RAW_DIR = str(DATA_DIR / "raw")

# --- LLM ---
# Секреты читаем из переменных окружения; в Streamlit Cloud их
# передают через [secrets], которые Streamlit раскладывает в env,
# либо мы читаем st.secrets в llm_helper (см. fallback).
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.proxyapi.ru/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "openai/gpt-4o-mini")
USE_OLLAMA = os.environ.get("USE_OLLAMA", "false").lower() == "true"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

# Синтетические данные (телеметрия/геология) в демо-базе привязаны к
# скважинам с числовым well_id. Реальные Volve-скважины телеметрии не имеют,
# поэтому разделы УЭЦН и геологии в отчёте помечаются как демонстрационные.
DEMO_WELL_ID = int(os.environ.get("DEMO_WELL_ID", "5"))


def ensure_data_dirs() -> None:
    """Создаёт каталоги данных, если их нет (первый запуск / облако)."""
    for d in (DATA_DIR, DRAFTS_DIR, CHARTS_DIR, SENT_DIR, EXCEL_DIR):
        Path(d).mkdir(parents=True, exist_ok=True)
