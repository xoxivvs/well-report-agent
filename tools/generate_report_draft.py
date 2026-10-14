"""
Инструмент 6: generate_report_draft
Действие (обратимое) — генерация PDF-черновика отчёта.

Версия 0.5: поддержка Volve + LLM-интерпретация + корректная обработка
отсутствующих данных (телеметрия, геология).
"""

import os
import sys
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

if __package__ in (None, ""):  # прямой запуск: python tools/generate_report_draft.py
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CHARTS_DIR, DRAFTS_DIR
from src.fonts import register_fonts

REPORTS_DIR = DRAFTS_DIR

COLOR_PRIMARY = colors.HexColor("#2F4F4F")
COLOR_SECONDARY = colors.HexColor("#FFA500")
COLOR_BG_LIGHT = colors.HexColor("#F5F7FA")
COLOR_BORDER = colors.HexColor("#E5E9F0")
COLOR_TEXT = colors.HexColor("#1A1A1A")
COLOR_TEXT_SEC = colors.HexColor("#5A6570")

FONT_CANDIDATES = []  # оставлено для обратной совместимости (не используется)

# Кроссплатформенный выбор шрифта (Windows / Linux / DejaVu из matplotlib)
FONT_NAME, FONT_BOLD = register_fonts()


# --- График ---
def plot_production(records, well_label, path):
    dates = [datetime.strptime(r["date"], "%Y-%m-%d") for r in records]
    oil = [r.get("oil_volume", r.get("oil_rate", 0)) for r in records]
    water = [r["water_cut"] for r in records]

    fig, ax1 = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor("white")
    ax1.set_facecolor("#F9FAFB")

    ax1.plot(dates, oil, color="#2F4F4F", linewidth=1.5, marker="o", markersize=2.5,
             label="Дебит нефти")
    ax1.fill_between(dates, oil, alpha=0.1, color="#2F4F4F")
    ax1.set_xlabel("Дата", fontsize=10)
    ax1.set_ylabel("Дебит нефти", color="#2F4F4F", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="#2F4F4F")
    ax1.tick_params(axis="x", rotation=45, labelsize=8)
    ax1.grid(True, linestyle="--", alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(dates, water, color="#FFA500", linewidth=1.2, linestyle="--",
             label="Обводнённость, %")
    ax2.set_ylabel("Обводнённость, %", color="#FFA500", fontsize=10)
    ax2.tick_params(axis="y", labelcolor="#FFA500")

    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(DateFormatter("%d.%m"))

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right",
               frameon=True, fontsize=9)

    plt.title(f"Динамика добычи — скважина {well_label}", fontsize=12, pad=12)
    plt.tight_layout()
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleC", parent=styles["Title"],
                                fontName=FONT_BOLD, fontSize=22, leading=28,
                                textColor=COLOR_PRIMARY, alignment=TA_LEFT, spaceAfter=4),
        "subtitle": ParagraphStyle("SubtitleC", parent=styles["Normal"],
                                   fontName=FONT_NAME, fontSize=11, leading=16,
                                   textColor=COLOR_TEXT_SEC, alignment=TA_LEFT),
        "h1": ParagraphStyle("H1C", parent=styles["Heading1"],
                             fontName=FONT_BOLD, fontSize=15, leading=20,
                             textColor=COLOR_PRIMARY, spaceBefore=14, spaceAfter=8),
        "h2": ParagraphStyle("H2C", parent=styles["Heading2"],
                             fontName=FONT_BOLD, fontSize=12, leading=16,
                             textColor=COLOR_PRIMARY, spaceBefore=10, spaceAfter=6),
        "body": ParagraphStyle("BodyC", parent=styles["BodyText"],
                               fontName=FONT_NAME, fontSize=10, leading=14,
                               textColor=COLOR_TEXT, alignment=TA_JUSTIFY),
        "bullet": ParagraphStyle("BulletC", parent=styles["BodyText"],
                                 fontName=FONT_NAME, fontSize=10, leading=14,
                                 textColor=COLOR_TEXT, leftIndent=14, bulletIndent=2),
        "caption": ParagraphStyle("CaptionC", parent=styles["BodyText"],
                                  fontName=FONT_NAME, fontSize=8, leading=12,
                                  textColor=COLOR_TEXT_SEC),
    }


def _table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
    ]
    if header:
        style += [
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ]
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), COLOR_BG_LIGHT))
    t.setStyle(TableStyle(style))
    return t


def _kpi_block(items):
    S = _styles()
    labels = [Paragraph(f"<font color='#5A6570' size='8'>{label}</font>", S["body"]) for label, _, _ in items]
    values = [Paragraph(f"<font color='{c}' size='16'><b>{v}</b></font>", S["body"]) for _, v, c in items]
    data = [labels, values]
    t = Table(data, colWidths=[4.2 * cm] * len(items), hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


# --- Анализ аномалий ---
def _analyze_anomalies(production, telemetry, geo):
    anomalies = []
    recommendations = []

    is_volve = (
        production.get("status") == "success"
        and "well_name" in (production.get("data") or {})
    )

    if is_volve:
        try:
            from tools.detect_anomalies_volve import detect_anomalies_volve
            volve_result = detect_anomalies_volve(production)
            for a in volve_result["anomalies"]:
                anomalies.append(a["description"])
                if a["type"] == "резкое_падение_дебита":
                    recommendations.append(
                        "[Высокий] Провести диагностику насосного оборудования "
                        "и оценку забойного давления."
                    )
                elif a["type"] == "скачок_обводнённости":
                    recommendations.append(
                        "[Средний] Оценить профиль притока (PLT), рассмотреть "
                        "изоляцию обводнённых интервалов."
                    )
                elif a["type"] == "длительный_простой":
                    recommendations.append(
                        "[Средний] Проанализировать причины простоя."
                    )
        except ImportError:
            anomalies.append("Модуль detect_anomalies_volve недоступен.")

    else:
        if production.get("status") == "success":
            agg = production["data"]["aggregates"]
            trend = production["data"]["trend"]
            avg_wc = agg.get("avg_water_cut", 0)

            if avg_wc > 80:
                anomalies.append(
                    f"Высокая обводнённость продукции ({avg_wc}%). Превышает порог 80%."
                )
                recommendations.append("[Высокий] Провести ГТМ по ограничению водопритока.")

            delta = trend.get("delta_oil") or trend.get("delta_oil_rate") or 0
            if trend["direction"] == "падение" and abs(delta) > 20:
                anomalies.append(f"Отрицательный тренд дебита ({delta}).")
                recommendations.append("[Высокий] Провести диагностику насосного оборудования.")

    # Телеметрия (синтетика, для Volve недоступна)
    if telemetry.get("status") == "success" and not is_volve:
        alarms = telemetry["data"]["alarms_summary"]
        runtime = telemetry["data"]["runtime_end"]
        if alarms.get("OVERHEAT", 0) > 0:
            anomalies.append(f"[ДЕМО] Перегрев УЭЦН: {alarms['OVERHEAT']} раз.")
            recommendations.append("[Высокий] Проверить систему охлаждения УЭЦН.")
        if alarms.get("OVERLOAD", 0) > 1:
            anomalies.append(f"[ДЕМО] Перегрузка УЭЦН: {alarms['OVERLOAD']} раз.")
        if runtime and runtime > 7000:
            anomalies.append(f"[ДЕМО] Наработка УЭЦН ({runtime} ч) — приближение к ППР.")
            recommendations.append("[Средний] Запланировать ППР.")

    # Геология (для Volve недоступна)
    if geo.get("status") == "success" and not is_volve:
        d = geo["data"]
        if d.get("reservoir_pressure") and d["reservoir_pressure"] < 160:
            anomalies.append(f"Пластовое давление ({d['reservoir_pressure']} атм) ниже начального.")

    if not anomalies:
        anomalies.append("Существенных отклонений за отчётный период не выявлено.")
        recommendations.append("[Низкий] Продолжить режим мониторинга без изменений.")

    return anomalies, recommendations


# --- Основная функция ---
def generate_report_draft(well_identifier, period, production, telemetry, geo, report_id=None):
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        os.makedirs(CHARTS_DIR, exist_ok=True)

        is_volve = (
            production.get("status") == "success"
            and "well_name" in (production.get("data") or {})
        )

        if is_volve:
            well_label = production["data"]["well_name"]
        else:
            well_label = f"№{well_identifier}"

        safe_name = str(well_identifier).replace("/", "_").replace(" ", "_").replace("№", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(REPORTS_DIR, f"report_well{safe_name}_{period}_{timestamp}.pdf")
        chart_path = os.path.join(CHARTS_DIR, f"chart_well{safe_name}_{timestamp}.png")

        if production["status"] == "success":
            plot_production(production["data"]["records"], well_label, chart_path)

        anomalies, recommendations = _analyze_anomalies(production, telemetry, geo)

        S = _styles()
        story = []

        # Титул
        story.append(Paragraph(f"Отчёт по скважине {well_label}", S["title"]))
        story.append(Paragraph(
            f"Период: <b>{period}</b> &nbsp;·&nbsp; "
            f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')} &nbsp;·&nbsp; "
            f"Тип: комплексный месячный",
            S["subtitle"]
        ))
        if is_volve:
            story.append(Paragraph(
                "<i>Источник данных: Equinor Volve Open Dataset (реальные данные месторождения).</i>",
                S["subtitle"]
            ))
        story.append(Spacer(1, 0.4 * cm))

        # 1. KPI
        story.append(Paragraph("1. Ключевые показатели", S["h1"]))
        kpi_items = []
        if production["status"] == "success":
            agg = production["data"]["aggregates"]
            unit = "м³/сут" if is_volve else "т/сут"
            avg_oil = agg.get("avg_oil") if is_volve else agg.get("avg_oil_rate")
            avg_wc = agg.get("avg_water_cut", 0)
            kpi_items.append(("Дебит нефти", f"{avg_oil} {unit}", "#2F4F4F"))
            kpi_items.append(("Обводнённость", f"{avg_wc}%",
                              "#EF4444" if avg_wc and avg_wc > 80 else "#2F4F4F"))
        if telemetry["status"] == "success" and not is_volve:
            kpi_items.append(("Наработка УЭЦН", f"{telemetry['data']['runtime_end']} ч", "#2F4F4F"))
        if geo["status"] == "success" and not is_volve:
            kpi_items.append(("Пласт. давление", f"{geo['data']['reservoir_pressure']} атм", "#2F4F4F"))
        if kpi_items:
            story.append(_kpi_block(kpi_items))
        story.append(Spacer(1, 0.4 * cm))

        # 2. Добыча
        story.append(Paragraph("2. Показатели добычи", S["h1"]))
        if production["status"] == "success":
            agg = production["data"]["aggregates"]
            trend = production["data"]["trend"]
            unit = "м³/сут" if is_volve else "т/сут"
            volume_unit = "м³" if is_volve else "т"
            avg_oil = agg.get("avg_oil") if is_volve else agg.get("avg_oil_rate")
            avg_wc = agg.get("avg_water_cut", 0)
            total_oil = agg.get("total_oil")
            days = agg.get("days_count")
            working = agg.get("working_days", days)
            delta_oil = trend.get("delta_oil") if is_volve else trend.get("delta_oil_rate")

            data = [
                ["Показатель", "Значение", "Комментарий"],
                ["Средний дебит нефти", f"{avg_oil} {unit}",
                 f"Рабочих дней: {working} из {days}"],
                ["Средняя обводнённость", f"{avg_wc} %",
                 "Высокая" if avg_wc and avg_wc > 80 else "В норме"],
                ["Суммарная добыча нефти", f"{total_oil} {volume_unit}",
                 f"за {days} дней"],
                ["Тренд дебита", f"{trend['direction']} ({delta_oil})",
                 "Разница 1-й и 2-й половины периода"],
            ]
            story.append(_table(data, col_widths=[6 * cm, 5 * cm, 6 * cm]))
        else:
            story.append(Paragraph("Данные о добыче за период отсутствуют.", S["body"]))
        story.append(Spacer(1, 0.4 * cm))

        # 3. УЭЦН
        story.append(Paragraph("3. Состояние оборудования (УЭЦН)", S["h1"]))
        if is_volve:
            story.append(Paragraph(
                "Данные телеметрии УЭЦН за период отсутствуют: открытый датасет "
                "Equinor Volve не содержит телеметрии насосного оборудования. "
                "Для полноценной диагностики требуется подключение к системе "
                "мониторинга скважин (SCADA/телеметрия).",
                S["body"]
            ))
        elif telemetry["status"] == "success":
            t = telemetry["data"]
            alarms_str = ", ".join(f"{k}: {v}" for k, v in t["alarms_summary"].items()) or "не зафиксировано"
            data = [
                ["Показатель", "Значение"],
                ["Наработка на конец периода", f"{t['runtime_end']} ч"],
                ["Тревог за период", str(len(t["alarms"]))],
                ["Типы тревог", alarms_str],
            ]
            story.append(_table(data, col_widths=[8 * cm, 9 * cm]))
        else:
            story.append(Paragraph("Телеметрия за период отсутствует.", S["body"]))
        story.append(Spacer(1, 0.4 * cm))

        # 4. Геология
        story.append(Paragraph("4. Геологические параметры", S["h1"]))
        if is_volve:
            story.append(Paragraph(
                "Структурированный геологический отчёт по скважине за период "
                "отсутствует в открытом датасете Volve. Датасет содержит "
                "сейсмические данные и каротаж в отдельном релизе, однако "
                "автоматическое извлечение из них готового отчёта невозможно.",
                S["body"]
            ))
        elif geo["status"] == "success":
            d = geo["data"]
            data = [
                ["Показатель", "Значение"],
                ["Пластовое давление", f"{d['reservoir_pressure']} атм"],
                ["Режим работы", d["mode"]],
                ["Дата геологического отчёта", d["date"] or "—"],
            ]
            story.append(_table(data, col_widths=[8 * cm, 9 * cm]))
        else:
            story.append(Paragraph("Геологический отчёт не найден.", S["body"]))
        story.append(Spacer(1, 0.5 * cm))

        # 5. График
        if production["status"] == "success" and os.path.exists(chart_path):
            story.append(PageBreak())
            story.append(Paragraph("5. Динамика добычи", S["h1"]))
            story.append(Image(chart_path, width=17 * cm, height=8 * cm))
            story.append(Paragraph(
                "На графике: дебит нефти (сплошная линия, левая ось) и "
                "обводнённость продукции (пунктир, правая ось).",
                S["caption"]
            ))
            story.append(Spacer(1, 0.5 * cm))

        # 6. Анализ и интерпретация
        story.append(Paragraph("6. Анализ и интерпретация", S["h1"]))
        story.append(Paragraph(
            "Ниже приведены выявленные аномалии и их техническая интерпретация "
            "в контексте режима работы скважины.",
            S["body"]
        ))
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph("<b>Выявленные аномалии:</b>", S["h2"]))
        for a in anomalies:
            story.append(Paragraph(f"• {a}", S["bullet"]))
        story.append(Spacer(1, 0.3 * cm))

        # LLM-интерпретация
        try:
            from src.llm_helper import generate_interpretation
            llm_interp = generate_interpretation(anomalies, well_label, period)
            story.append(Paragraph(
                "<b>Автоматическая интерпретация (LLM, локальная модель):</b>",
                S["h2"]
            ))
            story.append(Paragraph(llm_interp, S["body"]))
        except Exception as e:
            story.append(Paragraph(f"(LLM-интерпретация недоступна: {e})", S["caption"]))
        story.append(Spacer(1, 0.4 * cm))

        # 7. Рекомендации
        story.append(Paragraph("7. Рекомендации", S["h1"]))
        story.append(Paragraph(
            "Приоритет «Высокий» — реакция в течение 1–2 недель; «Средний» — "
            "в течение месяца; «Низкий» — плановое наблюдение.",
            S["body"]
        ))
        story.append(Spacer(1, 0.2 * cm))

        for r in recommendations:
            story.append(Paragraph(f"• {r}", S["bullet"]))

        try:
            from src.llm_helper import generate_recommendations_llm
            llm_recs = generate_recommendations_llm(anomalies, well_label, period)
            if llm_recs and "•" in llm_recs:
                story.append(Spacer(1, 0.2 * cm))
                story.append(Paragraph("<b>Дополнительно (LLM):</b>", S["h2"]))
                for line in llm_recs.split("\n"):
                    if line.strip():
                        story.append(Paragraph(line.strip(), S["bullet"]))
        except Exception:
            pass

        story.append(Spacer(1, 0.6 * cm))

        # Приложение
        story.append(Paragraph("Приложение: источники данных и допущения", S["h2"]))
        appendix_lines = [
            f"Скважина: {well_label}, период: {period}.",
            ("Источник данных: Equinor Volve Open Dataset (реальные данные)."
             if is_volve else
             "Источник данных: синтетическая база (демонстрация)."),
            ("Телеметрия УЭЦН и геологический отчёт отсутствуют в открытом "
             "датасете Volve — соответствующие разделы содержат пояснение."
             if is_volve else
             "Все разделы заполнены синтетическими данными."),
            "Метод выявления аномалий: трендовый анализ (14-дневное скользящее среднее).",
            "Данные приведены «как есть», без корректировки на погрешность измерений.",
            "Отчёт подготовлен автоматически ИИ-агентом и требует проверки инженером.",
        ]
        for line in appendix_lines:
            story.append(Paragraph(f"• {line}", S["bullet"]))

        story.append(Spacer(1, 0.6 * cm))
        story.append(_table([[""]], col_widths=[17 * cm], header=False))
        story.append(Paragraph(
            f"Отчёт сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M')} · "
            f"ИИ-агент подготовки отчётности · требует подтверждения инженером",
            S["caption"]
        ))

        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
            title=f"Отчёт по скважине {well_label} за {period}",
            author="ИИ-агент подготовки отчётности",
        )
        doc.build(story)

        return {
            "status": "success",
            "data": {
                "pdf_path": pdf_path,
                "chart_path": chart_path if os.path.exists(chart_path) else None,
                "anomalies": anomalies,
                "recommendations": recommendations,
            },
            "error": None,
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "data": None,
            "error": f"Ошибка генерации PDF: {e}\n{traceback.format_exc()}",
        }


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from tools.get_geo_report import get_geo_report
    from tools.get_production_data import get_production_data
    from tools.get_telemetry import get_telemetry

    print("=" * 70)
    print("ТЕСТ: VOLVE (реальные данные)")
    print("=" * 70)

    well_name = "15/9-F-14"
    period = "2014-06"

    prod = get_production_data(well_name, period, source="volve")
    tel = get_telemetry(5, period)
    geo = get_geo_report(5, period)

    result = generate_report_draft(well_name, period, prod, tel, geo)
    print(result)

    if result["status"] == "success":
        print(f"\nPDF: {result['data']['pdf_path']}")
        print(f"График: {result['data']['chart_path']}")
        for a in result["data"]["anomalies"]:
            print(f"  ! {a}")
        for r in result["data"]["recommendations"]:
            print(f"  > {r}")
