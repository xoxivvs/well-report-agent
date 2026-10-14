"""
Кроссплатформенный подбор шрифта для PDF и графиков.

Проблема: на Windows есть Arial, на Linux (Streamlit Cloud) — нет.
При этом для кириллицы нужен TTF с поддержкой Unicode, встроенные
шрифты reportlab (Helvetica) кириллицу не отображают.

Решение: ищем первый доступный шрифт в списке кандидатов:
1. Windows-шрифты (локальная разработка);
2. системные Linux-шрифты (DejaVu / Liberation);
3. DejaVuSans, который гарантированно идёт вместе с matplotlib.
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Пары (regular, bold) в порядке приоритета.
# Пути Windows — абсолютные; Linux/DejaVu подставляются ниже динамически.
_WINDOWS_FONTS = [
    (r"C:\Windows\Fonts\Arial.ttf", r"C:\Windows\Fonts\Arialbd.ttf"),
    (r"C:\Windows\Fonts\DejaVuSans.ttf", r"C:\Windows\Fonts\DejaVuSans-Bold.ttf"),
    (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
]
_LINUX_FONTS = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]


def _dejavu_from_matplotlib() -> list[tuple[str, str]]:
    """DejaVu из пакета matplotlib — доступен всегда, где стоит matplotlib."""
    ttf_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    regular = ttf_dir / "DejaVuSans.ttf"
    bold = ttf_dir / "DejaVuSans-Bold.ttf"
    if regular.exists():
        return [(str(regular), str(bold) if bold.exists() else str(regular))]
    return []


def _candidate_pairs() -> list[tuple[str, str]]:
    pairs = _WINDOWS_FONTS + _LINUX_FONTS + _dejavu_from_matplotlib()
    return [(r, b) for (r, b) in pairs if Path(r).exists()]


def register_fonts(custom_name: str = "CustomFont",
                   custom_bold_name: str = "CustomFontBold") -> tuple[str, str]:
    """
    Регистрирует TTF в reportlab и настраивает matplotlib.

    Returns:
        (font_name, font_bold_name) — имена для использования в reportlab.
        Если TTF не найден (маловероятно), возвращаются встроенные Helvetica
        (кириллица при этом может не отобразиться).
    """
    for regular, bold in _candidate_pairs():
        try:
            pdfmetrics.registerFont(TTFont(custom_name, regular))
            if Path(bold).exists():
                pdfmetrics.registerFont(TTFont(custom_bold_name, bold))
                bold_name = custom_bold_name
            else:
                bold_name = custom_name

            font_manager.fontManager.addfont(regular)
            plt.rcParams["font.family"] = font_manager.FontProperties(
                fname=regular).get_name()
            plt.rcParams["axes.unicode_minus"] = False
            return custom_name, bold_name
        except Exception:
            continue

    # Резервный вариант — встроенные шрифты reportlab
    plt.rcParams["axes.unicode_minus"] = False
    return "Helvetica", "Helvetica-Bold"
