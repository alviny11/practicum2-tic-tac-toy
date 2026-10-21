"""Окно матча: поле, клубы по краям и вопрос о футболисте."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
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

from football_ttt.agent import AgentError, verify_answer
from football_ttt.flags import paint_club_flag
from football_ttt.game import SIDES, Match

CELL = 124


class ClubBadge(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._name = ""
        self.setFixedSize(CELL, CELL)

    def set_club(self, name: str) -> None:
        self._name = name
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outer = QRect(1, 1, self.width() - 2, self.height() - 2)
        path = QPainterPath()
        path.addRoundedRect(float(outer.x()), float(outer.y()), float(outer.width()), float(outer.height()), 8, 8)
        painter.setClipPath(path)
        paint_club_flag(painter, self.rect(), self._name)
        painter.fillRect(self.rect(), QColor(16, 20, 28, 120))
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#2c3340"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(outer, 8, 8)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        text_rect = outer.adjusted(8, 8, -8, -8)
        painter.setPen(QColor(8, 10, 14, 180))
        painter.drawText(text_rect.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._name)
        painter.setPen(QColor("#f4f6f8"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._name)
        painter.end()


class CornerLabel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(CELL, CELL)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outer = QRect(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(QPen(QColor("#2c3340"), 2))
        painter.setBrush(QColor("#2a3140"))
        painter.drawRoundedRect(outer, 8, 8)
        painter.setPen(QColor("#d5dae3"))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            outer.adjusted(6, 6, -6, -6),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            "строка ↓\nстолбец →",
        )
        painter.end()


class CellButton(QPushButton):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(CELL, CELL)
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
        painter.setPen(QPen(QColor("#8b93a1"), 2))
        painter.setBrush(QColor("#323a48"))
        painter.drawRoundedRect(rect, 8, 8)
        if self._highlight and self._owner is None:
            painter.setPen(QPen(QColor("#c5ceda"), 3))
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
            "QDialog { background: #1c2330; color: #e6e9ef; }"
            "QLabel { color: #e6e9ef; }"
            "QLineEdit { background: #e7e9ee; color: #1c2330; padding: 6px; border-radius: 6px; }"
            "QPushButton { background: #3a4454; color: #e8eaee; padding: 8px 14px;"
            "border-radius: 8px; font-weight: 700; }"
            "QPushButton:hover { background: #4a5568; }"
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
    def __init__(self) -> None:
        super().__init__()
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
        root.setStyleSheet("background: #161a22; color: #d5d8de;")
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
            "QFrame#pitch { background: #1c2330; border: 4px solid #3d4654; border-radius: 16px; }"
        )
        pitch.setObjectName("pitch")
        grid = QGridLayout(pitch)
        grid.setSpacing(8)
        grid.setContentsMargins(12, 12, 12, 12)

        grid.addWidget(CornerLabel(), 0, 0)

        self.col_badges: list[ClubBadge] = []
        self.row_badges: list[ClubBadge] = []
        self.cells: list[list[CellButton]] = []
        for col in range(3):
            badge = ClubBadge()
            self.col_badges.append(badge)
            grid.addWidget(badge, 0, col + 1)
        for row in range(3):
            badge = ClubBadge()
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
            "QPushButton { background: #3a4454; color: #e8eaee; padding: 10px 16px;"
            "border-radius: 8px; font-weight: 700; }"
            "QPushButton:hover { background: #4a5568; }"
        )
        restart.clicked.connect(self._new_match)
        outer.addWidget(restart, alignment=Qt.AlignmentFlag.AlignLeft)

    def _refresh(self) -> None:
        for index, club in enumerate(self.match.cols):
            self.col_badges[index].set_club(club.name)
        for index, club in enumerate(self.match.rows):
            self.row_badges[index].set_club(club.name)
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
        self._note = "Проверяем ответ…"
        self._refresh()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            verdict = verify_answer(dialog.accepted_name or "", row_club.name, col_club.name)
        except AgentError as exc:
            self._note = f"Проверка не удалась: {exc} Ход остаётся вашим."
            return
        finally:
            QApplication.restoreOverrideCursor()
        shown = verdict.player_name or dialog.accepted_name
        if not verdict.accepted:
            self.match.pass_turn()
            self._note = f"«{shown}» не засчитан. {verdict.reason} Ход переходит сопернику."
            return
        self.match.claim(row, col)
        self._last = (row, col)
        side = SIDES[self.match.cells[row][col]]  # type: ignore[index]
        self._note = f"«{shown}» засчитан. {verdict.reason} Клетку забрали {side.title}."
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
