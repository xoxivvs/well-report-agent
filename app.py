"""
Streamlit-интерфейс для ИИ-агента подготовки отчётности.
Версия 0.5: поддержка реальных данных Volve.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import st_yled
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))  # корень проекта в sys.path

from src.config import DB_PATH, DEMO_WELL_ID, ensure_data_dirs

ensure_data_dirs()

st_yled.init()

# Фирменные стили (список свойств ограничен st-styled; см. element_styles.json)
st_yled.set("button", "background_color", "#FFA500")
st_yled.set("button", "color", "white")
st_yled.set("button_primary", "background_color", "#FFA500")
st_yled.set("button_primary", "color", "white")
st_yled.set("header", "color", "#2F4F4F")

from tools.export_to_excel import export_to_excel
from tools.generate_report_draft import generate_report_draft
from tools.get_confirmation_status import confirm_report, register_report
from tools.get_geo_report import get_geo_report
from tools.get_production_data import get_production_data
from tools.get_telemetry import get_telemetry
from tools.list_reports import get_stats, list_reports
from tools.list_wells import list_volve_periods, list_volve_wells
from tools.send_report import send_report

st.set_page_config(
    page_title="ИИ-агент отчётности по скважинам",
    page_icon="🛢️",
    layout="wide",
)


st.title("🛢️ ИИ-агент подготовки отчётности по скважинам")
st.caption("Реальные данные Volve → трендовый анализ → PDF + Excel → подтверждение → отправка")


# --- Боковая панель ---
with st.sidebar:
    st.header("⚙️ Параметры")

    volve_wells = list_volve_wells()
    if not volve_wells:
        st.error(
            "❌ Не найдены скважины Volve.\n\n"
            f"База данных: `{DB_PATH}`\n\n"
            "Локально: выполните `python src/database.py` и "
            "`python src/load_volve_data.py`."
        )
        st.stop()

    well_options = {
        f"{w['well_name']} ({w['records']} дней)": w["well_name"]
        for w in volve_wells
    }
    selected_label = st.selectbox("Скважина (Volve)", list(well_options.keys()))
    selected_well = well_options[selected_label]

    periods = list_volve_periods(selected_well)
    if periods:
        selected_period = st.selectbox("Период (год-месяц)", periods)
    else:
        selected_period = st.text_input("Период (YYYY-MM)", value="2014-06")

    recipient = st.text_input("Адресат (email)", value="engineer@example.com")

    st.markdown("---")
    st.markdown("**Режим работы:**")
    mode = st.radio(
        "Подтверждение отчёта",
        ["Интерактивный (я подтверждаю)", "Автоматический (для теста)"],
        index=0,
    )

    st.markdown("---")
    st.caption("Версия 0.5 • Pet-проект Ломакина В.Д.")


st.markdown(f"**Скважина:** `{selected_well}` &nbsp;|&nbsp; **Период:** `{selected_period}`")


col1, col2 = st.columns([2, 1])
with col1:
    generate_btn = st.button("🚀 Сгенерировать отчёт", type="primary", use_container_width=True)
with col2:
    st.caption(f"Время: {datetime.now().strftime('%H:%M:%S')}")


if "agent_state" not in st.session_state:
    st.session_state.agent_state = None


if generate_btn:
    st.session_state.agent_state = None
    progress_bar = st.progress(0, text="🚀 Запуск агента...")
    status_box = st.empty()

    import time

    # Шаг 1: данные
    progress_bar.progress(25, text="→ [1/4] Загрузка данных Volve...")
    status_box.info("→ [1/4] Загрузка данных Volve...")
    t0 = time.time()
    prod = get_production_data(selected_well, selected_period, source="volve")
    time_collect = round(time.time() - t0, 3)

    if prod["status"] == "empty":
        progress_bar.progress(100, text="⚠ Нет рабочих дней за период")
        st.warning(f"За период {selected_period} по скважине {selected_well} "
                   f"нет рабочих дней. Выберите другой период.")
        st.stop()

    if prod["status"] != "success":
        progress_bar.progress(100, text="❌ Ошибка загрузки данных")
        st.error(f"Ошибка: {prod.get('error')}")
        st.stop()

    # Шаг 2: телеметрия (синтетика — демо-данные)
    progress_bar.progress(50, text="→ [2/4] Телеметрия УЭЦН (демо)...")
    status_box.info("→ [2/4] Телеметрия УЭЦН (демонстрационные данные)...")
    tel = get_telemetry(DEMO_WELL_ID, selected_period)

    # Шаг 3: геология
    progress_bar.progress(75, text="→ [3/4] Геологический отчёт...")
    status_box.info("→ [3/4] Геологический отчёт...")
    geo = get_geo_report(DEMO_WELL_ID, selected_period)

    # Шаг 4: PDF
    progress_bar.progress(90, text="→ [4/4] Генерация PDF...")
    status_box.info("→ [4/4] Генерация PDF-черновика...")
    t0 = time.time()
    draft = generate_report_draft(selected_well, selected_period, prod, tel, geo)
    time_draft = round(time.time() - t0, 3)

    if draft["status"] != "success":
        progress_bar.progress(100, text="❌ Ошибка генерации PDF")
        st.error(f"Ошибка: {draft.get('error')}")
        st.stop()

    # Регистрируем отчёт
    report_id = register_report(selected_well, selected_period, "monthly")

    total_time = round(time_collect + time_draft, 3)

    progress_bar.progress(100, text="✅ Готово!")
    status_box.success(f"✅ Отчёт готов за {total_time:.2f} сек")

    st.session_state.agent_state = {
        "well_name": selected_well,
        "period": selected_period,
        "report_id": report_id,
        "pdf_path": draft["data"]["pdf_path"],
        "chart_path": draft["data"]["chart_path"],
        "anomalies": draft["data"]["anomalies"],
        "recommendations": draft["data"]["recommendations"],
        "production": prod,
        "telemetry": tel,
        "geo": geo,
        "time_total": total_time,
        "time_collect": time_collect,
        "time_draft": time_draft,
    }


# --- Показ результата ---
state = st.session_state.agent_state

if state:
    st.markdown("---")
    st.subheader("📄 Черновик отчёта")

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Скважина", state["well_name"])
    col_b.metric("Период", state["period"])
    col_c.metric("ID отчёта", state["report_id"])
    col_d.metric("⏱ Время", f"{state['time_total']:.2f} сек")

    # Экономия
    st.markdown("---")
    st.subheader("💰 Экономия времени")

    manual_hours = 4.0
    manual_sec = manual_hours * 3600
    agent_sec = state["time_total"] or 1
    saved_sec = manual_sec - agent_sec

    e1, e2, e3 = st.columns(3)
    e1.metric("Ручная работа", f"{manual_hours:.0f} ч")
    e2.metric("Агент", f"{agent_sec:.2f} сек")
    e3.metric("⚡ Ускорение", f"{manual_sec / agent_sec:.0f}x")

    st.info(
        f"**Сэкономлено: {saved_sec/3600:.2f} часов на одном отчёте.** "
        f"За 100 отчётов — это ~{saved_sec*100/3600:.0f} часов рабочего времени."
    )

    # Аномалии
    st.markdown("---")
    st.subheader("⚠️ Аномалии и рекомендации")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Выявленные аномалии**")
        for a in state["anomalies"]:
            st.warning(a)
    with col_r:
        st.markdown("**Рекомендации**")
        for r in state["recommendations"]:
            st.info(r)

    # Скачать
    pdf_path = state["pdf_path"]
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        xlsx_result = export_to_excel(
            state["well_name"], state["period"],
            state["production"], state["telemetry"], state["geo"]
        )

        st.markdown("---")
        st.subheader("📥 Скачать отчёт")
        col_pdf, col_xlsx = st.columns(2)

        with col_pdf:
            st.download_button(
                "📄 Скачать PDF",
                data=pdf_bytes,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                use_container_width=True,
            )

        with col_xlsx:
            if xlsx_result["status"] == "success":
                with open(xlsx_result["data"]["xlsx_path"], "rb") as f:
                    xlsx_bytes = f.read()
                st.download_button(
                    "📊 Скачать Excel",
                    data=xlsx_bytes,
                    file_name=os.path.basename(xlsx_result["data"]["xlsx_path"]),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.error(f"Excel: {xlsx_result['error']}")

        # Предпросмотр PDF
        try:
            import base64
            st.markdown("**Предпросмотр PDF:**")
            base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.caption(f"(Предпросмотр недоступен: {e})")

    # Подтверждение
    st.markdown("---")
    st.subheader("✅ Подтверждение")

    if mode.startswith("Интерактивный"):
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ Подтвердить и отправить", type="primary", use_container_width=True):
                confirm_report(state["report_id"], "approved")
                result = send_report(state["report_id"], pdf_path, recipient)
                if result["status"] == "success":
                    st.success(f"📤 Отчёт отправлен: {result['data']['sent_path']}")
                    st.balloons()
                else:
                    st.error(f"Ошибка: {result['error']}")
        with col_no:
            if st.button("❌ Отклонить", use_container_width=True):
                confirm_report(state["report_id"], "rejected")
                st.warning("Отчёт отклонён.")
    else:
        if st.button("⚡ Авто-подтвердить и отправить", use_container_width=True):
            confirm_report(state["report_id"], "approved")
            result = send_report(state["report_id"], pdf_path, recipient)
            if result["status"] == "success":
                st.success(f"📤 Отчёт отправлен: {result['data']['sent_path']}")
                st.balloons()
            else:
                st.error(f"Ошибка: {result['error']}")


# --- История ---
st.markdown("---")
st.subheader("📊 Статистика и история")

stats = get_stats()
if stats:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Всего отчётов", stats.get("total", 0))
    m2.metric("Черновиков", stats.get("drafts", 0))
    m3.metric("Подтверждено", stats.get("approved", 0))
    m4.metric("Отправлено", stats.get("sent", 0))
    m5.metric("Одобрено, %", f"{stats.get('approval_rate', 0)}%")

reports = list_reports(limit=20)
if reports:
    import pandas as pd
    df = pd.DataFrame([
        {
            "ID": r["report_id"],
            "Скважина": r["well_id"],
            "Период": r["period"],
            "Тип": r["report_type"],
            "Статус": r["status"],
            "Подтверждение": r["confirmation_status"] or "—",
            "Создан": r["created_at"][:19] if r["created_at"] else "—",
        }
        for r in reports
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Пока нет ни одного отчёта.")
