"""Тесты центральной конфигурации и путей."""

from pathlib import Path

from src import config


def test_base_dir_is_repo_root(repo_root):
    assert config.BASE_DIR == repo_root


def test_db_path_is_absolute(data_dir):
    assert Path(config.DB_PATH).is_absolute()
    assert Path(config.DB_PATH).parent == data_dir


def test_data_dir_respects_env(data_dir):
    assert Path(config.DATA_DIR) == data_dir


def test_output_dirs_are_absolute():
    for d in (config.DRAFTS_DIR, config.CHARTS_DIR, config.SENT_DIR,
              config.EXCEL_DIR, config.GEO_REPORTS_DIR):
        assert Path(d).is_absolute()


def test_ensure_data_dirs_creates_dirs():
    config.ensure_data_dirs()
    for d in (config.DRAFTS_DIR, config.CHARTS_DIR, config.SENT_DIR, config.EXCEL_DIR):
        assert Path(d).is_dir()
