"""Пул европейских клубов и случайный выбор шестёрки на матч."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Club:
    name: str
    primary: str
    secondary: str


# Десять известных европейских клубов. На каждый матч берутся шесть разных.
TOP_EUROPEAN_CLUBS: tuple[Club, ...] = (
    Club("Реал Мадрид", "#f5f5f5", "#0d1b4c"),
    Club("Барселона", "#a50044", "#004d98"),
    Club("Бавария", "#dc052d", "#0066b2"),
    Club("Манчестер Сити", "#6cabdd", "#1c2c5b"),
    Club("Ливерпуль", "#c8102e", "#00b2a9"),
    Club("Ювентус", "#ffffff", "#000000"),
    Club("ПСЖ", "#004170", "#da291c"),
    Club("Челси", "#034694", "#dba111"),
    Club("Интер", "#010e80", "#000000"),
    Club("Арсенал", "#ef0107", "#063672"),
)


def pick_match_clubs(rng: random.Random | None = None) -> tuple[tuple[Club, ...], tuple[Club, ...]]:
    """Случайно выбрать 6 клубов: 3 слева (строки) и 3 сверху (столбцы)."""
    chooser = rng or random
    chosen = chooser.sample(TOP_EUROPEAN_CLUBS, 6)
    rows = tuple(chosen[:3])
    cols = tuple(chosen[3:])
    return rows, cols
