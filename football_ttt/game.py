"""Правила поля 3×3: очередь, занятость, победа и ничья.

Проверка «играл ли футболист за оба клуба» сюда не входит —
её подменяет случайный ответ в интерфейсе.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from football_ttt.clubs import Club, pick_match_clubs

SIZE = 3


@dataclass(frozen=True)
class Side:
    key: str
    title: str
    color: str
    mark: str


SIDES: tuple[Side, Side] = (
    Side("home", "Хозяева", "#6d7682", "▲"),
    Side("away", "Гости", "#3d5168", "●"),
)


class Match:
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self.rows: tuple[Club, ...] = ()
        self.cols: tuple[Club, ...] = ()
        self.cells: list[list[int | None]] = []
        self.turn = 0
        self.winner: int | None = None
        self.draw = False
        self.reset()

    @property
    def finished(self) -> bool:
        return self.winner is not None or self.draw

    @property
    def current(self) -> Side:
        return SIDES[self.turn]

    def reset(self) -> None:
        self.rows, self.cols = pick_match_clubs(self._rng)
        self.cells = [[None for _ in range(SIZE)] for _ in range(SIZE)]
        self.turn = 0
        self.winner = None
        self.draw = False

    def clubs_at(self, row: int, col: int) -> tuple[Club, Club]:
        return self.rows[row], self.cols[col]

    def occupied(self, row: int, col: int) -> bool:
        return self.cells[row][col] is not None

    def claim(self, row: int, col: int) -> bool:
        """Закрасить клетку текущим игроком. False, если ход недопустим."""
        if self.finished or self.occupied(row, col):
            return False
        self.cells[row][col] = self.turn
        self._resolve()
        if not self.finished:
            self.turn = 1 - self.turn
        return True

    def pass_turn(self) -> None:
        """Неверный ответ: клетка пустая, ходит соперник."""
        if not self.finished:
            self.turn = 1 - self.turn

    def _resolve(self) -> None:
        lines = self._lines()
        for line in lines:
            owner = line[0]
            if owner is not None and all(cell == owner for cell in line):
                self.winner = owner
                return
        if all(cell is not None for row in self.cells for cell in row):
            self.draw = True

    def _lines(self) -> list[list[int | None]]:
        rows = [list(row) for row in self.cells]
        cols = [[self.cells[r][c] for r in range(SIZE)] for c in range(SIZE)]
        diag = [self.cells[i][i] for i in range(SIZE)]
        anti = [self.cells[i][SIZE - 1 - i] for i in range(SIZE)]
        return rows + cols + [diag, anti]
