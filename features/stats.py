"""
Статистика (волна 5): каждая выполненная команда пишется в data/stats.db.

    «Кеша, сколько раз ты включала музыку за неделю?»
    «статистика за месяц», «какие команды я использую чаще всего»
"""

import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta

import core
from config import STATS_DB
from core import registry
from nlu import normalize, apply_synonyms

_lock = threading.Lock()
_conn = None
db_path = STATS_DB


def _db():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _conn.execute("CREATE TABLE IF NOT EXISTS usage (ts REAL, name TEXT, source TEXT)")
        _conn.execute("CREATE INDEX IF NOT EXISTS usage_ts ON usage(ts)")
    return _conn


def use_db(path):
    """Другая база (для тестов)."""
    global _conn, db_path
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn, db_path = None, path


def record(source, name, text="", response="", ts=None):
    if source == "kesha":
        return
    with _lock:
        db = _db()
        db.execute("INSERT INTO usage VALUES (?, ?, ?)", (ts or time.time(), name, source))
        db.commit()


core.on_command(record)


def count(name=None, since=None):
    q, args = "SELECT COUNT(*) FROM usage WHERE 1=1", []
    if name:
        q += " AND name = ?"
        args.append(name)
    if since is not None:
        q += " AND ts >= ?"
        args.append(since.timestamp())
    with _lock:
        return _db().execute(q, args).fetchone()[0]


def top(since=None, limit=5):
    q, args = "SELECT name, COUNT(*) c FROM usage", []
    if since is not None:
        q += " WHERE ts >= ?"
        args.append(since.timestamp())
    q += " GROUP BY name ORDER BY c DESC LIMIT ?"
    args.append(limit)
    with _lock:
        return _db().execute(q, args).fetchall()


# ---------- разбор вопроса ----------
_PERIODS = [
    (r"\bсегодня\b", "сегодня", lambda now: now.replace(hour=0, minute=0, second=0, microsecond=0)),
    (r"\bвчера\b", "со вчерашнего дня", lambda now: (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)),
    (r"\bза (эту |последнюю )?неделю\b|\bна этой неделе\b|\bза 7 дней\b", "за неделю", lambda now: now - timedelta(days=7)),
    (r"\bза (этот |последний )?месяц\b|\bза 30 дней\b", "за месяц", lambda now: now - timedelta(days=30)),
    (r"\bза (этот |последний )?год\b", "за год", lambda now: now - timedelta(days=365)),
    (r"\bза вс[её] время\b|\bвсего\b", "за всё время", lambda now: None),
]


def parse_period(text, now, default=("за всё время", None)):
    for rx, label, since in _PERIODS:
        m = re.search(rx, text)
        if m:
            return label, since(now), m.span()
    return default[0], default[1], None


def _stems(text):
    return [w[:5] for w in normalize(text).split() if len(w) >= 3]


def find_command(phrase):
    """Какую команду имеют в виду: «включала музыку» -> play_music. Без выполнения."""
    phrase = phrase.strip()
    if not phrase:
        return None
    for text in (phrase, apply_synonyms(normalize(phrase))):
        for cmd in core._matching(text):
            if cmd["name"] not in _STATS_CMDS:
                return cmd
    # по основам слов: «включала музыку» ~ «включи музыку»
    want = set(_stems(phrase))
    best, best_score = None, 0
    for cmd in registry.commands:
        if cmd["name"] in _STATS_CMDS:
            continue
        for p in cmd["patterns"]:
            ps = _stems(p)
            if ps and all(s in want for s in ps) and len(ps) > best_score:
                best, best_score = cmd, len(ps)
    return best


_STATS_CMDS = {"stats_query"}
_QUESTION_WORDS = ["сколько раз", "как часто", "ты", "я", "мы", "меня", "мне", "уже", "вообще"]


def _times(n):
    return f"{n} раз" + ("а" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "")


@registry.command(
    ["сколько раз", "как часто", "статистика", "моя статистика", "какие команды чаще",
     "самые частые команды", "что я чаще всего", "чем я пользуюсь чаще"],
    "Статистика использования", "Статистика", priority=9,
)
def stats_query(text):
    now = datetime.now()
    t = normalize(text)
    label, since, span = parse_period(t, now)
    if "сколько раз" in t or "как часто" in t:
        rest = t if span is None else t[:span[0]] + " " + t[span[1]:]
        for w in _QUESTION_WORDS:
            rest = re.sub(rf"(?<!\w){w}(?!\w)", " ", rest)
        cmd = find_command(" ".join(rest.split()))
        if cmd is None:
            if not re.search(r"\b(ты|я|мы)\b", t):
                return None   # «сколько раз в неделю бегать» — вопрос для GigaChat
            return "Не понял, какую команду посчитать. Например: «сколько раз ты включала музыку за неделю»."
        n = count(cmd["name"], since)
        return f"«{cmd['description']}» — {_times(n)} {label}."
    rows = top(since if span else now - timedelta(days=7))
    label = label if span else "за неделю"
    if not rows:
        return f"{label.capitalize()} команд ещё не было."
    names = {c["name"]: c["description"] for c in registry.commands}
    names["ai"] = "вопросы GigaChat"
    total = count(None, since if span else now - timedelta(days=7))
    parts = [f"{names.get(n, n)} — {c}" for n, c in rows]
    return f"{label.capitalize()} всего {_times(total)}. Чаще всего: " + "; ".join(parts) + "."
