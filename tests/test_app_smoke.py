"""
Smoke-тест Streamlit-приложения: скрипт app.py должен выполняться
без исключений при первом рендере (то, что падает в облаке, ловим здесь).
"""

from pathlib import Path

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def test_app_renders_without_exception(data_dir):
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()

    assert not at.exception, [str(e) for e in at.exception]
    # Заголовок приложения отрисован
    assert any("отчётности" in t.value for t in at.title)


def test_app_has_sidebar_controls(data_dir):
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()

    assert not at.exception
    # В сайдбаре есть выбор скважины и периода
    assert len(at.sidebar.selectbox) >= 2


def test_app_generate_report_flow(data_dir):
    """Полный цикл: нажатие «Сгенерировать отчёт» без исключений."""
    at = AppTest.from_file(str(APP_PATH), default_timeout=180)
    at.run()
    assert not at.exception

    # Кнопка генерации — первая кнопка на странице
    at.button[0].click().run(timeout=180)
    assert not at.exception, [str(e) for e in at.exception]

    # Появились метрики (карточки с результатом) вместо пустой страницы
    assert at.metric, "Ожидались метрики после генерации отчёта"
