"""Карьера футболиста со страницы Википедии.

Имя и два клуба приходят снаружи. Функция скачивает статью и смотрит
только клубы из карточки игрока, не весь текст страницы.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from football_ttt.agent.errors import AgentError

_USER_AGENT = "FootballTTT/0.1 (educational tic-tac-toe; local)"
_CLUB_FIELD = re.compile(r"^\|\s*clubs\d+\s*=\s*(.*?)\s*$", re.MULTILINE)
_RU_CLUBS_FIELD = re.compile(r"^\|\s*клубы\s*=")
_TOP_LEVEL_FIELD = re.compile(r"^\|\s*[^\d\s]")
_LINK = re.compile(r"\[\[([^\[\]|#]+)(?:#[^\[\]|]*)?(?:\|([^\[\]]+))?\]\]")
_RESERVE = re.compile(r"\b(?:ii|iii|reserves|youth|under[\s-]?\d+|u\d{2}|b|б)\b")
_CYRILLIC = re.compile(r"[а-яё]")

# Как клуб называется в игре и как он встречается в карточках ru/en Википедии.
_CLUB_ALIASES: dict[str, tuple[str, ...]] = {
    "Реал Мадрид": ("real madrid", "реал мадрид"),
    "Барселона": ("fc barcelona", "barcelona", "барселона"),
    "Бавария": ("bayern munich", "fc bayern", "bayern munchen", "бавария"),
    "Манчестер Сити": ("manchester city", "манчестер сити"),
    "Ливерпуль": ("liverpool", "ливерпуль"),
    "Ювентус": ("juventus", "ювентус"),
    "ПСЖ": ("paris saint germain", "пари сен жермен", "псж"),
    "Челси": ("chelsea", "челси"),
    "Интер": ("inter milan", "internazionale", "fc internazionale", "интер", "интернационале"),
    "Арсенал": ("arsenal", "арсенал"),
}

# Чужие клубы с похожим именем не должны проходить как «наш».
_CLUB_REJECTS: dict[str, tuple[str, ...]] = {
    "Барселона": ("barcelona sc", "barcelona sporting"),
    "Интер": ("inter miami", "интер майами", "internacional", "inter turku"),
    "Арсенал": ("arsenal tula", "arsenal de sarandi", "arsenal kyiv", "арсенал тула"),
    "Челси": ("chelsea fc (los angeles)",),
}


@dataclass(frozen=True)
class CareerLookup:
    player_name: str
    page_title: str | None
    clubs: tuple[str, ...]
    found: bool
    played_for_both: bool


def player_played_for_clubs(player_name: str, club_a: str, club_b: str) -> CareerLookup:
    """Прочитать карьеру с сайта и сказать, есть ли в ней оба клуба."""
    _require_known_club(club_a)
    _require_known_club(club_b)
    title, labels, played = _find_career(player_name, club_a, club_b)
    if title is None:
        return CareerLookup(player_name, None, (), False, False)
    return CareerLookup(player_name, title, tuple(labels), True, played)


def _require_known_club(club_name: str) -> None:
    if club_name not in _CLUB_ALIASES:
        raise AgentError(f"Неизвестный клуб «{club_name}».")


def _find_career(player_name: str, club_a: str, club_b: str) -> tuple[str | None, list[str], bool]:
    """Выбрать статью, в карьере которой больше всего совпадений с двумя клубами."""
    partial: tuple[str, list[str]] | None = None
    first: tuple[str, list[str]] | None = None
    for page in _search_titles(player_name):
        wikitext = _fetch_wikitext(page)
        if wikitext is None:
            continue
        labels = _career_labels(wikitext)
        if not labels:
            continue
        title = page[1]
        if first is None:
            first = (title, labels)
        matched_a = _matches_club(labels, club_a)
        matched_b = _matches_club(labels, club_b)
        if matched_a and matched_b:
            return title, labels, True
        if (matched_a or matched_b) and partial is None:
            partial = (title, labels)
    chosen = partial or first
    if chosen is None:
        return None, [], False
    return chosen[0], chosen[1], False


def _search_titles(player_name: str) -> list[tuple[str, str]]:
    languages = ("ru", "en") if _CYRILLIC.search(player_name.lower()) else ("en", "ru")
    found: list[tuple[str, str]] = []
    for language in languages:
        payload = _get(
            language,
            {
                "action": "query",
                "list": "search",
                "srsearch": player_name,
                "srlimit": "5",
                "format": "json",
            },
        )
        for item in payload.get("query", {}).get("search", []):
            title = item.get("title")
            pair = (language, title)
            if title and pair not in found:
                found.append(pair)
    return found[:8]


_WIKITEXT_CACHE: dict[tuple[str, str], str | None] = {}


def _fetch_wikitext(page: tuple[str, str]) -> str | None:
    if page in _WIKITEXT_CACHE:
        return _WIKITEXT_CACHE[page]
    language, title = page
    payload = _get(
        language,
        {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        },
    )
    if "error" in payload:
        _WIKITEXT_CACHE[page] = None
        return None
    wikitext = payload.get("parse", {}).get("wikitext")
    if not isinstance(wikitext, str) or not wikitext.strip():
        _WIKITEXT_CACHE[page] = None
        return None
    _WIKITEXT_CACHE[page] = wikitext
    return wikitext


def _career_labels(wikitext: str) -> list[str]:
    infobox = wikitext.split("\n==", 1)[0]
    labels: list[str] = []
    for raw in _CLUB_FIELD.findall(infobox):
        labels.extend(_club_labels(raw))
    labels.extend(_ru_career_labels(infobox))
    return labels


def _ru_career_labels(infobox: str) -> list[str]:
    labels: list[str] = []
    collecting = False
    for line in infobox.splitlines():
        if _RU_CLUBS_FIELD.match(line):
            collecting = True
            labels.extend(_link_labels(line.split("=", 1)[1]))
            continue
        if collecting and _TOP_LEVEL_FIELD.match(line):
            break
        if collecting and "фарм" not in line:
            labels.extend(_link_labels(line))
    return labels


def _link_labels(raw: str) -> list[str]:
    return [group.strip() for match in _LINK.finditer(raw) for group in match.groups() if group]


def _club_labels(raw: str) -> list[str]:
    labels = [group.strip() for match in _LINK.finditer(raw) for group in match.groups() if group]
    if labels:
        return labels
    plain = re.sub(r"\{\{[^{}]*\}\}", " ", raw)
    plain = re.sub(r"<[^>]+>", " ", plain).strip()
    return [plain] if plain else []


def _matches_club(labels: list[str], club_name: str) -> bool:
    aliases = _CLUB_ALIASES[club_name]
    rejects = _CLUB_REJECTS.get(club_name, ())
    for label in labels:
        norm = _normalize(label)
        if not norm or _RESERVE.search(norm):
            continue
        if any(reject in norm for reject in rejects):
            continue
        if any(_phrase_in(alias, norm) for alias in aliases):
            return True
    return False


def _phrase_in(alias: str, norm: str) -> bool:
    return re.search(rf"(?:^| ){re.escape(_normalize(alias))}(?: |$)", norm) is not None


def _normalize(text: str) -> str:
    text = text.lower().replace("ё", "е").replace("ü", "u").replace("–", " ").replace("—", " ")
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9а-я ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _get(language: str, params: dict[str, str]) -> dict:
    url = f"https://{language}.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    delay = 1.0
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 3:
                time.sleep(delay)
                delay *= 2
                continue
            raise AgentError("Не удалось прочитать страницу Википедии.") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AgentError("Не удалось прочитать страницу Википедии.") from exc
    raise AgentError("Не удалось прочитать страницу Википедии.")
