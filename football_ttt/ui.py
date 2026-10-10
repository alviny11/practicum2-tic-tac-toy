"""Окно матча: поле, клубы по краям и вопрос о футболисте."""

from __future__ import annotations

import random
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from football_ttt.game import SIDES, Match


def _readable(hex_color: str) -> str:
    color = QColor(hex_color)
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return "#111111" if luminance > 160 else "#f7f7f7"


class ClubBadge(QLabel):
    def __init__(self, name: str, primary: str, secondary: str) -> None:
        super().__init__(name)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumSize(132, 72)
        ink = _readable(primary)
        self.setStyleSheet(
            "QLabel {"
            f"background: {primary}; color: {ink};"
            f"border: 3px solid {secondary}; border-radius: 10px;"
            "font-weight: 700; padding: 6px;"
            "}"
        )


class CellButton(QPushButton):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(118, 118)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._owner: int | None = None
        self._highlight = False
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def set_owner(self, owner: int | None, highlight: bool) -> None:
        self._owner = owner
        self._highlight = highlight
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(6, 6, -6, -6)
        painter.setPen(QPen(QColor("#e8f5e9"), 2))
        painter.setBrush(QColor(27, 94, 32, 210))
        painter.drawRoundedRect(rect, 8, 8)
        if self._highlight and self._owner is None:
            painter.setPen(QPen(QColor("#ffeb3b"), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
        if self._owner is None:
            painter.end()
            return
        side = SIDES[self._owner]
        color = QColor(side.color)
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#ffffff"), 3))
        painter.drawEllipse(rect.adjusted(18, 18, -18, -18))
        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, side.mark)
        painter.end()


class PlayerDialog(QDialog):
    """Вопрос «кто играл за оба клуба» — под полем, рядом с выбранной клеткой."""

    def __init__(self, row_club: str, col_club: str, side_title: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Футболист")
        self.setModal(True)
        self.accepted_name: str | None = None
        self.setStyleSheet(
            "QDialog { background: #102418; color: #f4fff6; }"
            "QLabel { color: #f4fff6; }"
            "QLineEdit { background: #ffffff; color: #102418; padding: 6px; border-radius: 6px; }"
            "QPushButton { padding: 8px 14px; border-radius: 8px; font-weight: 700; }"
        )
        layout = QVBoxLayout(self)
        title = QLabel(f"Ход: {side_title}")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        question = QLabel(
            f"Назовите футболиста, который выступал и за «{row_club}», и за «{col_club}»."
        )
        question.setWordWrap(True)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Имя футболиста")
        buttons = QHBoxLayout()
        submit = QPushButton("Назвать")
        skip = QPushButton("Не могу назвать")
        submit.clicked.connect(self._submit)
        skip.clicked.connect(self.reject)
        self.name_edit.returnPressed.connect(self._submit)
        buttons.addWidget(submit)
        buttons.addWidget(skip)
        layout.addWidget(title)
        layout.addWidget(question)
        layout.addWidget(self.name_edit)
        layout.addLayout(buttons)
        self.resize(420, 180)

    def _submit(self) -> None:
        text = self.name_edit.text().strip()
        if not text:
            self.accepted_name = None
            self.reject()
            return
        self.accepted_name = text
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, rng: random.Random | None = None) -> None:
        super().__init__()
        self._rng = rng or random.Random()
        self.match = Match()
        self._busy = False
        self._last: tuple[int, int] | None = None
        self._note = ""
        self.setWindowTitle("Футбольные крестики-нолики")
        self.resize(760, 720)
        self._build()
        self._refresh()

    def _build(self) -> None:
        root = QWidget()
        root.setStyleSheet("background: #0c1a12; color: #f4fff6;")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 16, 18, 16)

        header = QLabel("Футбольные крестики-нолики")
        header.setFont(QFont("", 18, QFont.Weight.Bold))
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setFont(QFont("", 12))
        outer.addWidget(header)
        outer.addWidget(self.status)

        pitch = QFrame()
        pitch.setStyleSheet(
            "QFrame#pitch { background: #1b5e20; border: 4px solid #e8f5e9; border-radius: 16px; }"
        )
        pitch.setObjectName("pitch")
        grid = QGridLayout(pitch)
        grid.setSpacing(8)
        grid.setContentsMargins(12, 12, 12, 12)

        corner = QLabel("строка ↓\nстолбец →")
        corner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner.setStyleSheet("color: #e8f5e9;")
        grid.addWidget(corner, 0, 0)

        self.col_badges: list[ClubBadge] = []
        self.row_badges: list[ClubBadge] = []
        self.cells: list[list[CellButton]] = []
        for col in range(3):
            badge = ClubBadge("", "#1b5e20", "#e8f5e9")
            self.col_badges.append(badge)
            grid.addWidget(badge, 0, col + 1)
        for row in range(3):
            badge = ClubBadge("", "#1b5e20", "#e8f5e9")
            self.row_badges.append(badge)
            grid.addWidget(badge, row + 1, 0)
            row_cells: list[CellButton] = []
            for col in range(3):
                button = CellButton()
                button.clicked.connect(lambda _checked=False, r=row, c=col: self._on_cell(r, c))
                grid.addWidget(button, row + 1, col + 1)
                row_cells.append(button)
            self.cells.append(row_cells)
        outer.addWidget(pitch)

        hint = QLabel(
            "Клик по свободной клетке — пересечение клуба строки и клуба столбца. "
            "Верный ответ закрашивает клетку цветом вашей команды."
        )
        hint.setWordWrap(True)
        outer.addWidget(hint)

        restart = QPushButton("Новый матч")
        restart.setCursor(Qt.CursorShape.PointingHandCursor)
        restart.setStyleSheet(
            "QPushButton { background: #ffeb3b; color: #102418; padding: 10px 16px;"
            "border-radius: 8px; font-weight: 700; }"
            "QPushButton:hover { background: #fff176; }"
        )
        restart.clicked.connect(self._new_match)
        outer.addWidget(restart, alignment=Qt.AlignmentFlag.AlignLeft)

    def _refresh(self) -> None:
        for index, club in enumerate(self.match.cols):
            self._paint_badge(self.col_badges[index], club.name, club.primary, club.secondary)
        for index, club in enumerate(self.match.rows):
            self._paint_badge(self.row_badges[index], club.name, club.primary, club.secondary)
        for row in range(3):
            for col in range(3):
                owner = self.match.cells[row][col]
                self.cells[row][col].set_owner(owner, self._last == (row, col))
                self.cells[row][col].setEnabled(not self.match.finished and owner is None)
        if self.match.winner is not None:
            side = SIDES[self.match.winner]
            text = f"Победа: {side.title}. Три клетки в ряд."
        elif self.match.draw:
            text = "Ничья: поле заполнено, трёх в ряд нет."
        else:
            side = self.match.current
            text = f"Сейчас ходят {side.title} ({side.mark}). Выберите свободную клетку."
        if self._note and not self.match.finished:
            text = f"{self._note} {text}"
        self.status.setText(text)

    @staticmethod
    def _paint_badge(badge: ClubBadge, name: str, primary: str, secondary: str) -> None:
        badge.setText(name)
        ink = _readable(primary)
        badge.setStyleSheet(
            "QLabel {"
            f"background: {primary}; color: {ink};"
            f"border: 3px solid {secondary}; border-radius: 10px;"
            "font-weight: 700; padding: 6px;"
            "}"
        )

    def _on_cell(self, row: int, col: int) -> None:
        if self._busy or self.match.finished or self.match.occupied(row, col):
            return
        self._busy = True
        try:
            self._ask_and_resolve(row, col)
        finally:
            self._busy = False
        self._refresh()

    def _ask_and_resolve(self, row: int, col: int) -> None:
        row_club, col_club = self.match.clubs_at(row, col)
        dialog = PlayerDialog(row_club.name, col_club.name, self.match.current.title, self)
        anchor = self.cells[row][col].mapToGlobal(self.cells[row][col].rect().bottomLeft())
        dialog.move(anchor.x() - 40, anchor.y() + 8)
        named = dialog.exec() == QDialog.DialogCode.Accepted and bool(dialog.accepted_name)
        if not named:
            self.match.pass_turn()
            self._note = "Футболист не назван. Клетка пустая, ход переходит сопернику."
            return
        correct = self._rng.random() < 0.5
        player_name = dialog.accepted_name
        if not correct:
            self.match.pass_turn()
            self._note = f"«{player_name}» не засчитан. Клетка пустая, ход переходит сопернику."
            return
        self.match.claim(row, col)
        self._last = (row, col)
        side = SIDES[self.match.cells[row][col]]  # type: ignore[index]
        self._note = f"«{player_name}» засчитан. Клетку забрали {side.title}."
        if self.match.finished:
            self._announce_end()

    def _announce_end(self) -> None:
        if self.match.winner is not None:
            text = f"Победили {SIDES[self.match.winner].title}."
        else:
            text = "Ничья."
        QMessageBox.information(self, "Матч окончен", text)

    def _new_match(self) -> None:
        if self._busy:
            return
        self._last = None
        self._note = ""
        self.match.reset()
        self._refresh()


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
