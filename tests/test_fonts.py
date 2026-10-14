"""Тесты подбора шрифтов (кроссплатформенность PDF/графиков)."""

from pathlib import Path

from src.fonts import _candidate_pairs, register_fonts


def test_candidate_pairs_exist_on_disk():
    pairs = _candidate_pairs()
    assert pairs, "Не найден ни один шрифт (ожидался минимум DejaVu из matplotlib)"
    for regular, bold in pairs:
        assert Path(regular).exists()


def test_register_fonts_returns_names():
    name, bold = register_fonts(custom_name="TestFont", custom_bold_name="TestFontBold")
    assert isinstance(name, str) and name
    assert isinstance(bold, str) and bold


def test_matplotlib_dejavu_available_without_windows_fonts(monkeypatch):
    """На Linux/облаке Windows-шрифтов нет — должен подхватиться DejaVu matplotlib."""
    import src.fonts as fonts

    monkeypatch.setattr(fonts, "_WINDOWS_FONTS", [])
    monkeypatch.setattr(fonts, "_LINUX_FONTS", [])
    pairs = fonts._candidate_pairs()
    assert pairs, "DejaVu из matplotlib не найден — PDF без кириллицы"
    assert "DejaVu" in Path(pairs[0][0]).name
