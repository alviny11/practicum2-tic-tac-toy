"""Простые рисунки клубных флагов для подложки названия.

Это поля флагов (полосы и цвета клуба), без гербов.
"""

from __future__ import annotations

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QColor, QPainter

# Спокойный запасной тон, если имени нет в таблице.
FALLBACK = "#3a4250"


def paint_club_flag(painter: QPainter, rect: QRect, club_name: str) -> None:
    painter.save()
    painter.setPen(QColor(0, 0, 0, 0))
    drawer = _DRAW.get(club_name)
    if drawer is None:
        painter.fillRect(rect, QColor(FALLBACK))
    else:
        drawer(painter, rect)
    painter.restore()


def _bands(painter: QPainter, rect: QRect, colors: list[str], vertical: bool) -> None:
    count = len(colors)
    if vertical:
        width = rect.width() / count
        for index, color in enumerate(colors):
            left = rect.left() + round(index * width)
            right = rect.left() + round((index + 1) * width)
            painter.fillRect(QRect(left, rect.top(), right - left, rect.height()), QColor(color))
    else:
        height = rect.height() / count
        for index, color in enumerate(colors):
            top = rect.top() + round(index * height)
            bottom = rect.top() + round((index + 1) * height)
            painter.fillRect(QRect(rect.left(), top, rect.width(), bottom - top), QColor(color))


def _real(painter: QPainter, rect: QRect) -> None:
    # Белый флаг клуба.
    painter.fillRect(rect, QColor("#f4f5f7"))


def _barcelona(painter: QPainter, rect: QRect) -> None:
    # Сеньера: жёлтое поле и четыре красные полосы.
    painter.fillRect(rect, QColor("#f6d36b"))
    stripe = rect.height() / 9
    for index in (1, 3, 5, 7):
        top = rect.top() + round(index * stripe)
        bottom = rect.top() + round((index + 1) * stripe)
        painter.fillRect(QRect(rect.left(), top, rect.width(), bottom - top), QColor("#c45c5c"))


def _bayern(painter: QPainter, rect: QRect) -> None:
    _bands(painter, rect, ["#c45c5c", "#f4f5f7"], vertical=False)


def _city(painter: QPainter, rect: QRect) -> None:
    painter.fillRect(rect, QColor("#7f9bb5"))


def _liverpool(painter: QPainter, rect: QRect) -> None:
    painter.fillRect(rect, QColor("#9a4a4a"))


def _juventus(painter: QPainter, rect: QRect) -> None:
    _bands(painter, rect, ["#1c1c1c", "#f4f5f7"] * 3, vertical=True)


def _psg(painter: QPainter, rect: QRect) -> None:
    # Синее поле и красная вертикаль по центру, как на форме Эхтера.
    painter.fillRect(rect, QColor("#1e3a5f"))
    band = rect.width() // 5
    left = rect.left() + (rect.width() - band) // 2
    painter.fillRect(QRect(left, rect.top(), band, rect.height()), QColor("#8d3d3d"))


def _chelsea(painter: QPainter, rect: QRect) -> None:
    painter.fillRect(rect, QColor("#2f4d73"))


def _inter(painter: QPainter, rect: QRect) -> None:
    _bands(painter, rect, ["#243e66", "#1a1a1a"] * 3, vertical=True)


def _arsenal(painter: QPainter, rect: QRect) -> None:
    # Белые края и широкая красная середина — схема домашней формы.
    painter.fillRect(rect, QColor("#f4f5f7"))
    side = rect.width() // 5
    painter.fillRect(
        QRect(rect.left() + side, rect.top(), rect.width() - 2 * side, rect.height()),
        QColor("#9a4545"),
    )


_DRAW = {
    "Реал Мадрид": _real,
    "Барселона": _barcelona,
    "Бавария": _bayern,
    "Манчестер Сити": _city,
    "Ливерпуль": _liverpool,
    "Ювентус": _juventus,
    "ПСЖ": _psg,
    "Челси": _chelsea,
    "Интер": _inter,
    "Арсенал": _arsenal,
}
