"""Локальная модель достаёт имя футболиста из произвольной строки."""

from __future__ import annotations

import json
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path

from football_ttt.agent.errors import AgentError

_MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/"
    "qwen2.5-1.5b-instruct-q4_k_m.gguf"
)
_MODEL_NAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
_MIN_BYTES = 200_000_000
_SYSTEM = (
    "Extract the footballer's name from the user message and nothing else. "
    "The message may be Russian and may contain extra words. "
    "Keep the spelling from the message. Do not translate the name and do not invent a different person. "
    'Reply with one JSON object only: {"player_name": "name"} '
    'or {"player_name": ""} when the message does not name a person. '
    'Phrases such as "не знаю", "пропуск" and "пас" are not names.'
)
_JSON_OBJECT = re.compile(r"\{[^{}]*\}")

_model = None


def extract_player_name(user_text: str) -> str:
    """Отдать строку ввода модели и вернуть имя футболиста."""
    text = user_text.strip()
    if not text:
        return ""
    model = _load_model()
    raw = _complete(model, text)
    return _parse_name(raw)


def _complete(model, user_text: str) -> str:
    try:
        response = model.create_chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_text},
            ],
            temperature=0,
            max_tokens=64,
        )
    except Exception as exc:
        raise AgentError("Модель не смогла прочитать строку.") from exc
    try:
        return str(response["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise AgentError("Модель вернула пустой ответ.") from exc


def _parse_name(raw: str) -> str:
    payload = raw.strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?", "", payload).strip()
        payload = payload.removesuffix("```").strip()
    match = _JSON_OBJECT.search(payload)
    if match is None:
        raise AgentError("Модель не назвала футболиста.")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AgentError("Модель не назвала футболиста.") from exc
    name = data.get("player_name", "")
    if not isinstance(name, str):
        raise AgentError("Модель не назвала футболиста.")
    return name.strip()


def _load_model():
    global _model
    if _model is None:
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise AgentError("Не установлен пакет llama-cpp-python.") from exc
        path = _ensure_model()
        try:
            _model = Llama(model_path=str(path), n_ctx=1024, n_threads=4, verbose=False)
        except Exception as exc:
            raise AgentError("Не удалось загрузить модель.") from exc
    return _model


def _ensure_model() -> Path:
    destination = Path.home() / ".cache" / "football-ttt" / _MODEL_NAME
    if destination.is_file() and destination.stat().st_size >= _MIN_BYTES:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".part")
    request = urllib.request.Request(_MODEL_URL, headers={"User-Agent": "FootballTTT/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        raise AgentError("Не удалось скачать модель для разбора имени.") from exc
    if temporary.stat().st_size < _MIN_BYTES:
        temporary.unlink(missing_ok=True)
        raise AgentError("Файл модели скачался неполностью.")
    temporary.replace(destination)
    return destination
