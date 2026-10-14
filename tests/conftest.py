"""
Общие фикстуры для тестов.

Ключевая идея: тесты НЕ трогают реальную БД и каталоги с результатами.
Перед импортом модулей проекта подменяем каталог данных через переменную
окружения WELL_REPORT_DATA_DIR и копируем туда эталонные данные.
Так как инструменты читают пути через src.config на этапе импорта,
переменную нужно выставить ДО первого импорта src.config — поэтому код
выполняется на уровне модуля conftest.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_SEED_DATA = REPO_ROOT / "data"

# --- Изолированный каталог данных (до импорта src.config) ---
# Держим внутри .pytest_cache — он уже в .gitignore и не засоряет репозиторий.
_TMP_ROOT = REPO_ROOT / ".pytest_cache" / "test-data"
if _TMP_ROOT.exists():
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)
_TMP_ROOT.mkdir(parents=True, exist_ok=True)
_TMP_DATA = Path(tempfile.mkdtemp(prefix="run-", dir=_TMP_ROOT))
os.environ["WELL_REPORT_DATA_DIR"] = str(_TMP_DATA)

# Копируем эталонную БД и геологические PDF-отчёты
shutil.copy(_SEED_DATA / "wells.db", _TMP_DATA / "wells.db")
shutil.copytree(_SEED_DATA / "geo_reports", _TMP_DATA / "geo_reports",
                dirs_exist_ok=True)
for _d in ("drafts", "charts", "sent", "excel"):
    (_TMP_DATA / _d).mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return _TMP_DATA


@pytest.fixture(scope="session")
def volve_well():
    """Первая доступная скважина Volve и её последний период."""
    from tools.list_wells import list_volve_periods, list_volve_wells

    wells = list_volve_wells()
    assert wells, "В тестовой БД нет скважин Volve"
    name = wells[0]["well_name"]
    periods = list_volve_periods(name)
    assert periods, f"Нет периодов для {name}"
    return {"name": name, "period": periods[0]}


@pytest.fixture(scope="session")
def demo_geo_period():
    """Период, для которого есть синтетический геологический PDF."""
    from tools.list_wells import list_volve_wells  # noqa: F401  (прогрев импорта)

    return "2026-09"
