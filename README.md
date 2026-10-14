# 🛢️ ИИ-агент подготовки отчётности по скважинам

Веб-приложение (Streamlit), которое автоматизирует подготовку комплексного
отчёта по нефтегазовой скважине: собирает данные о добыче, телеметрии и
геологии, выявляет аномалии, формирует PDF/Excel-отчёт и требует
подтверждения инженера перед «отправкой».

Работает на **реальных данных открытого датасета Equinor Volve**
(месторождение в Северном море) + демонстрационные синтетические данные.

---

## 🎯 Задача

Сократить время подготовки отчёта по скважине с 2–6 часов до секунд за счёт
автоматического сбора и сведения разнородных данных.

- **Пользователь:** инженер-технолог / геолог нефтедобывающего предприятия.
- **Результат:** PDF-отчёт (показатели добычи, УЭЦН, геология, аномалии,
  рекомендации) + Excel-выгрузка с исходными данными.

---

## ✨ Возможности

- 📥 Сбор данных из SQLite (добыча Volve, телеметрия УЭЦН, геологические PDF);
- 📈 Трендовый анализ и **детерминированное** выявление аномалий
  (падение дебита, скачок обводнённости, длительный простой);
- 🤖 Интерпретация и рекомендации через LLM (внешний API или локальный Ollama);
- 📄 PDF-отчёт с графиками (reportlab + matplotlib) и Excel-выгрузка (openpyxl);
- 👤 Human-in-the-loop: отправка возможна только после подтверждения;
- 🗂 Журнал отчётов, статистика, история;
- 💰 Оценка экономии времени прямо в интерфейсе.

---

## 🏗 Архитектура

```
Streamlit UI (app.py)
   │
   ├─ get_production_data   → добыча (production_volve)
   ├─ get_telemetry         → телеметрия УЭЦН (демо)
   ├─ get_geo_report        → парсинг PDF геологии
   ├─ detect_anomalies_*    → детерминированный анализ
   ├─ generate_report_draft → PDF + графики (+ LLM-интерпретация)
   ├─ export_to_excel       → Excel
   ├─ register/confirm      → журнал подтверждений (SQLite)
   └─ send_report           → «отправка» после approve
```

- **LLM не считает метрики.** Все показатели и аномалии — детерминированный
  Python-код. Модель используется только для интерпретации и рекомендаций.
- **CLI-агент на LangGraph** (`src/agent_graph.py`, `src/run_agent.py`) —
  альтернативный запуск того же конвейера из терминала.

---

## 📁 Структура проекта

```
well-report-agent/
├── app.py                      # Streamlit-приложение (точка входа продукта)
├── src/
│   ├── config.py               # единая конфигурация путей и настроек
│   ├── periods.py              # разбор отчётного периода (валидация)
│   ├── fonts.py                # кроссплатформенный подбор шрифта (кириллица)
│   ├── llm_helper.py           # LLM: API / Ollama, чтение секретов
│   ├── agent_graph.py          # граф LangGraph (CLI-агент)
│   ├── agent_state.py          # состояние агента
│   ├── run_agent.py            # CLI: auto / manual режимы
│   ├── database.py             # схема БД
│   ├── load_volve_data.py      # загрузка данных Volve в SQLite
│   ├── seed_data.py            # синтетические данные (демо)
│   └── generate_pdf_reports.py # генерация PDF-заглушек геологии
├── tools/                      # инструменты агента (по одному модулю на шаг)
├── scripts/                    # служебные утилиты (диагностика, графики)
├── tests/                      # pytest-тесты
├── data/
│   ├── wells.db                # SQLite с данными (в репозитории)
│   ├── raw/                    # исходный датасет Volve
│   └── geo_reports/            # PDF геологии
├── .github/workflows/ci.yml    # CI: ruff + pytest
├── requirements.txt            # зависимости рантайма
├── requirements-dev.txt        # зависимости для разработки/CI
└── .env.example                # шаблон переменных окружения
```

Каталоги `data/drafts`, `data/charts`, `data/sent`, `data/excel` создаются
приложением автоматически и в репозиторий не попадают.

---

## 🚀 Быстрый старт (локально)

```powershell
py -m venv venv
venv\Scripts\Activate.ps1            # Windows
# source venv/bin/activate            # Linux/macOS

pip install -r requirements.txt
```

Данные уже в репозитории (`data/wells.db`). Запуск приложения:

```powershell
streamlit run app.py
```

Откроется `http://localhost:8501`.

### Переменные окружения (LLM)

Скопируйте `.env.example` → `.env` и заполните:

```ini
LLM_API_KEY=...
LLM_BASE_URL=https://api.proxyapi.ru/v1
LLM_MODEL=openai/gpt-4o-mini
```

Без ключа приложение работает, но в отчёте вместо LLM-интерпретации будет
строка «LLM недоступен».

### Пересборка данных (опционально)

```powershell
python src/database.py             # создать БД
python src/load_volve_data.py      # загрузить Volve
python src/generate_pdf_reports.py # PDF геологии (демо)
```

---

## 🖥 CLI-режим (LangGraph)

```powershell
python src/run_agent.py --mode manual --query "Отчёт по скважине 5 за сентябрь 2026"
python src/run_agent.py --mode auto
```

---

## 🧪 Тестирование

```powershell
pip install -r requirements-dev.txt
ruff check src tools tests scripts app.py   # линт
pytest tests/ -v                            # тесты (47 шт.)
```

Тесты включают smoke-тест Streamlit-приложения
(`streamlit.testing.AppTest`): проверяют, что `app.py` рендерится и полный
цикл генерации отчёта проходит без исключений.

---

## ☁️ Деплой на Streamlit Community Cloud

1. Залейте репозиторий на GitHub.
2. На [share.streamlit.io](https://share.streamlit.io) → **New app** →
   выберите репозиторий, ветку `main`, главный файл — `app.py`.
3. В **Settings → Secrets** добавьте ключи (см. `.streamlit/secrets.toml.example`):

   ```toml
   LLM_API_KEY = "..."
   LLM_BASE_URL = "https://api.proxyapi.ru/v1"
   LLM_MODEL = "openai/gpt-4o-mini"
   ```

4. Deploy.

### Заметки про облако

- Файловая система на Community Cloud **эфемерна**: сгенерированные PDF/Excel
  и записи в журнал исчезают при перезапуске приложения. Для постоянного
  хранения данных нужен внешний сторедж или своя БД.
- Каталог данных можно переопределить переменной `WELL_REPORT_DATA_DIR`
  (например, `/tmp/well-report-data`).
- Если хостинг read-only — задайте `WELL_REPORT_DATA_DIR` в secrets.
- Шрифты: на Linux автоматически используется DejaVu из matplotlib
  (кириллица поддерживается, ничего доустанавливать не нужно).

---

## 🧠 Ключевые решения

1. **Разделение ответственности:** метрики — детерминированный код, LLM —
   только интерпретация и рекомендации.
2. **Human-in-the-loop:** `send_report` — единственное необратимое действие,
   выполняется только при статусе `approved`.
3. **Законные пустые результаты:** нет данных за период → `empty`, а не
   `error`. Некорректный ввод (кривой период) → понятный `error`.
4. **Кроссплатформенность:** единая конфигурация путей и подбор шрифтов —
   проект одинаково работает на Windows и в Linux-облаке.

---

## ⚠️ Ограничения (важно понимать)

- **Телеметрия УЭЦН и геологические отчёты — демонстрационные (синтетика).**
  Для реальных Volve-скважин этих данных нет, поэтому соответствующие
  разделы помечаются как демо (см. `DEMO_WELL_ID`).
- **Отправка отчёта — заглушка:** результат пишется в `data/sent/*.txt`,
  реальная отправка по e-mail/СЭД не выполняется.
- Данные — открытый датасет Volve, используются в учебных целях.

---

## 🛠 Стек

| Компонент | Технология |
|-----------|------------|
| Язык | Python 3.12 |
| UI | Streamlit + st-styled |
| Оркестрация | LangGraph |
| Данные | pandas, SQLite |
| Графики | matplotlib |
| PDF | reportlab, pdfplumber |
| Excel | openpyxl |
| LLM | OpenAI-совместимый API / Ollama |
| Линт / тесты / CI | ruff, pytest, GitHub Actions |

---

## 👤 Автор

**Ломакин В.Д.** — учебный pet-проект.

Данные: [Equinor Volve Open Dataset](https://www.equinor.com/energy/volve-data-sharing).
