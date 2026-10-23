"""
Контекст сессии (волна 2): помним последние 2–3 реплики, чтобы понимать
«А в Питере?» после «Погода в Москве».
Сессия своя для каждого источника (voice / telegram / website / ...).
"""

import re
import threading
import time
from collections import deque

from config import SESSION_STEPS, SESSION_TTL

# «а в питере», «и во владивостоке», «а про собак», «а 30» — только такие формы,
# чтобы не перехватывать обычные вопросы вроде «а ты кто?».
_FOLLOWUP = re.compile(
    r"^(?:а|и|ну а|а как насчет|а что насчет)\s+"
    r"(?:(?:в|во|на|про|о|об|по|для)\s+(?P<arg>\S+(?:\s\S+)?)|(?P<num>\d+))$"
)

# Признаки того, что вопрос зависит от предыдущего диалога.
_CONTEXT_WORDS = {"там", "он", "она", "оно", "они", "его", "ее", "их", "это",
                  "этот", "эта", "тогда", "еще", "тоже", "оттуда", "туда"}


class Session:
    def __init__(self):
        self._lock = threading.Lock()
        self._entries = deque(maxlen=SESSION_STEPS)

    def remember(self, text: str, response: str, followup: "str | None" = None):
        """followup — шаблон вида «погода в {arg}», если команду можно уточнить."""
        with self._lock:
            self._entries.append({
                "text": text, "response": response,
                "followup": followup, "ts": time.monotonic(),
            })

    def recent(self) -> list:
        now = time.monotonic()
        with self._lock:
            return [e for e in self._entries if now - e["ts"] <= SESSION_TTL]

    def resolve_followup(self, norm_text: str) -> "str | None":
        """«а в питере» -> «погода в питере», если недавно была подходящая команда."""
        m = _FOLLOWUP.match(norm_text)
        if not m:
            return None
        arg = m.group("arg") or m.group("num")
        for e in reversed(self.recent()):
            if e["followup"]:
                return e["followup"].format(arg=arg)
        return None

    def context(self) -> str:
        """Последние реплики текстом — для подсказки GigaChat."""
        lines = []
        for e in self.recent():
            lines.append(f"Пользователь: {e['text']}")
            lines.append(f"Кеша: {e['response']}")
        return "\n".join(lines)

    def clear(self):
        with self._lock:
            self._entries.clear()


def looks_like_followup(norm_text: str) -> bool:
    """Вопрос, который без предыдущего диалога не понять."""
    words = norm_text.split()
    if not words:
        return False
    if words[0] in ("а", "и", "ну"):
        return True
    return len(words) <= 5 and any(w in _CONTEXT_WORDS for w in words)


_sessions = {}
_sessions_lock = threading.Lock()


def get(source: str) -> Session:
    with _sessions_lock:
        if source not in _sessions:
            _sessions[source] = Session()
        return _sessions[source]


def reset():
    with _sessions_lock:
        _sessions.clear()
