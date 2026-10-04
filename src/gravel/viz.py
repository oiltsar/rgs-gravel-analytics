"""Единый стиль графиков проекта (matplotlib)."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

FIG_DIR = Path(__file__).resolve().parents[2] / "reports" / "figures"

# Категориальная палитра — фиксированный порядок, проверена на различимость при дальтонизме
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948",
)
GRAY = "#a3a29c"
SURFACE = "#fcfcfb"
TEXT, TEXT_2, TEXT_3 = "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e6e5e0"
# Последовательная шкала (один тон, светлый -> тёмный) для тепловых карт
BLUES = mpl.colors.LinearSegmentedColormap.from_list(
    "blues", ["#f3f7fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)


def setup() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
        "font.family": ["PT Sans", "Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 10.5,
        "text.color": TEXT, "axes.labelcolor": TEXT_2, "xtick.color": TEXT_2, "ytick.color": TEXT_2,
        "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "axes.titlelocation": "left", "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.titlepad": 30, "legend.frameon": False, "lines.linewidth": 2,
        "xtick.major.size": 0, "ytick.major.size": 0,
    })


def subtitle(ax, text: str) -> None:
    """Подзаголовок-вывод под заголовком графика."""
    ax.text(0, 1.025, text, transform=ax.transAxes, color=TEXT_2, fontsize=10, va="bottom")


def save(fig, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path)
    return path
