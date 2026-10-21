"""Агент проверки ответа.

Строка ввода уходит в модель. Модель достаёт имя футболиста.
Имя вместе с двумя клубами клетки передаётся в функцию, которая
читает карьеру на сайте. По её ответу клетка либо закрашивается, либо нет.
"""

from __future__ import annotations

from dataclasses import dataclass

from football_ttt.agent.llm import extract_player_name
from football_ttt.agent.lookup import player_played_for_clubs


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    player_name: str
    reason: str


def verify_answer(user_text: str, club_a: str, club_b: str) -> Verdict:
    """Проверить строку игрока для пересечения двух клубов."""
    player_name = extract_player_name(user_text)
    if not player_name:
        return Verdict(False, "", "В строке не нашлось имени футболиста.")
    career = player_played_for_clubs(player_name, club_a, club_b)
    if not career.found:
        return Verdict(False, player_name, "Страница футболиста в Википедии не найдена.")
    if not career.played_for_both:
        return Verdict(
            False,
            player_name,
            f"На странице «{career.page_title}» нет карьеры и в «{club_a}», и в «{club_b}».",
        )
    return Verdict(
        True,
        player_name,
        f"На странице «{career.page_title}» есть карьера и в «{club_a}», и в «{club_b}».",
    )
