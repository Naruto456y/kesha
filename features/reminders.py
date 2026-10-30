"""
Напоминания, будильник и таймер (волна 4).

    «Кеша, напомни через 20 минут выключить плиту»
    «разбуди меня в 7», «поставь будильник на 6:30»
    «таймер на 5 минут», «какие напоминания», «отмени будильник», «стоп»

Хранятся в data/reminders.json — переживают перезапуск. Фоновый поток раз
в секунду проверяет, не пора ли. Когда пора: всплывашка Windows + голос +
сообщение в UI; будильник и таймер ещё и звенят, пока не скажешь «стоп».
Если напоминание поставили из Telegram — оно придёт и в Telegram.
"""

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta

import core
from config import REMINDERS_FILE
from core import registry
from timeparse import parse_when, parse_duration, say_duration, say_moment

MISSED_GRACE = timedelta(hours=12)   # пропущенные (ПК был выключен) старше — не напоминаем
KIND_TITLES = {"reminder": "Напоминание", "alarm": "Будильник", "timer": "Таймер"}


class ReminderStore:
    def __init__(self, path=REMINDERS_FILE):
        self.path = path
        self._lock = threading.RLock()
        self._items = None

    def _load(self):
        if self._items is not None:
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self._items = data if isinstance(data, list) else []
        except (OSError, ValueError):
            self._items = []

    def _save(self):
        tmp = f"{self.path}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._items, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError as e:
            print(f"[reminders] не удалось сохранить: {e}")

    def add(self, kind, due: datetime, text="", source="app", duration=None):
        item = {"id": uuid.uuid4().hex[:8], "kind": kind, "due": due.isoformat(timespec="seconds"),
                "text": text, "source": source, "created": datetime.now().isoformat(timespec="seconds")}
        if duration:
            item["duration"] = int(duration)
        with self._lock:
            self._load()
            self._items.append(item)
            self._save()
        return item

    def pending(self, kind=None):
        with self._lock:
            self._load()
            items = [i for i in self._items if kind is None or i["kind"] == kind]
        return sorted(items, key=lambda i: i["due"])

    def remove(self, ids):
        ids = set(ids)
        with self._lock:
            self._load()
            before = len(self._items)
            self._items = [i for i in self._items if i["id"] not in ids]
            if len(self._items) != before:
                self._save()
            return before - len(self._items)

    def pop_due(self, now: datetime):
        """Забрать всё, чему пора сработать. -> (сработать, просрочено слишком давно)."""
        with self._lock:
            self._load()
            due, stale, keep = [], [], []
            for i in self._items:
                t = datetime.fromisoformat(i["due"])
                if t > now:
                    keep.append(i)
                elif now - t > MISSED_GRACE:
                    stale.append(i)
                else:
                    due.append(i)
            if due or stale:
                self._items = keep
                self._save()
        return due, stale


store = ReminderStore()
_thread = None
_stop = threading.Event()


# ============================================================
#  СРАБАТЫВАНИЕ
# ============================================================
def message_for(item, now: datetime) -> str:
    kind, text = item["kind"], item.get("text") or ""
    due = datetime.fromisoformat(item["due"])
    late = now - due > timedelta(minutes=2)
    if kind == "alarm":
        msg = "Подъём! Будильник." + (f" {text}" if text else "")
    elif kind == "timer":
        msg = f"Таймер на {say_duration(item.get('duration', 0))} закончился!"
        if text:
            msg += f" {text}"
    else:
        msg = f"Напоминаю: {text}" if text else "Вы просили напомнить."
    if late:
        msg += f" (пропущено, было на {due.strftime('%H:%M')})"
    return msg


def fire(item, now: "datetime | None" = None):
    now = now or datetime.now()
    msg = message_for(item, now)
    print(f"[reminders] {msg}")
    if item["kind"] in ("alarm", "timer"):
        try:
            from voice import sfx
            if item["kind"] == "alarm":
                sfx.alarm_start()
            else:
                sfx.alarm_start(max_sec=30)
        except Exception as e:
            print(f"[reminders] звонок: {e}")
    core.announce(msg, title=KIND_TITLES.get(item["kind"], "Кеша"),
                  speak=item["kind"] == "reminder")
    if item.get("source") == "telegram":
        try:
            from features import messenger
            messenger.send_to_owners(msg)
        except Exception as e:
            print(f"[reminders] Telegram: {e}")


def check_due(now: "datetime | None" = None):
    now = now or datetime.now()
    due, stale = store.pop_due(now)
    for item in stale:
        print(f"[reminders] слишком старое, пропускаю: {item}")
    for item in due:
        try:
            fire(item, now)
        except Exception as e:
            print(f"[reminders] ошибка срабатывания: {e}")
    return due


def _loop():
    while not _stop.wait(1.0):
        check_due()


def start():
    """Запустить фоновую проверку (один раз)."""
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, daemon=True, name="reminders")
    _thread.start()


def stop():
    _stop.set()


# ============================================================
#  КОМАНДЫ
# ============================================================
_REMIND_WORDS = ["поставь напоминание", "создай напоминание", "сделай напоминание",
                 "добавь напоминание", "напомнить", "напомни"]
_ALARM_WORDS = ["поставь будильник", "заведи будильник", "установи будильник",
                "включи будильник", "будильник", "разбуди меня", "разбуди"]
_FILLER = {"мне", "нам", "пожалуйста", "о", "об", "про", "что", "чтобы", "том", "на", "-", "и"}


def _strip(text, words):
    t = text
    for w in sorted(words, key=len, reverse=True):
        t = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", " ", t)
    tokens = t.split()
    while tokens and tokens[0] in _FILLER:
        tokens.pop(0)
    while tokens and tokens[-1] in _FILLER:
        tokens.pop()
    return " ".join(tokens)


def _when_phrase(dt: datetime, now: datetime) -> str:
    left = (dt - now).total_seconds()
    if left < 3600:
        return "через " + say_duration(max(60, round(left / 60) * 60) if left >= 60 else left)
    return say_moment(dt, now)


@registry.command(
    _REMIND_WORDS,
    "Напоминание", "Напоминания", priority=7,
)
def add_reminder(text):
    now = datetime.now()
    when = parse_when(text, now)
    if when is None:
        return "Когда напомнить? Например: «напомни через 20 минут выключить плиту»."
    if when.dt <= now:
        return "Это время уже прошло."
    task = _strip(when.rest, _REMIND_WORDS)
    store.add("reminder", when.dt, task, core.current_source())
    start()
    return f"Хорошо, напомню {_when_phrase(when.dt, now)}" + (f": {task}" if task else ".")


@registry.command(
    _ALARM_WORDS,
    "Будильник", "Напоминания", priority=7,
)
def add_alarm(text):
    now = datetime.now()
    when = parse_when(text, now, prefer_morning=True)
    if when is None:
        return "На какое время поставить будильник? Например: «разбуди меня в 7»."
    note = _strip(when.rest, _ALARM_WORDS)
    store.add("alarm", when.dt, note, core.current_source())
    start()
    hours, rem = divmod(int((when.dt - now).total_seconds()), 3600)
    left = f"через {say_duration(hours * 3600 + rem // 60 * 60)}" if hours or rem >= 60 else "меньше чем через минуту"
    return f"Будильник на {say_moment(when.dt, now)}, это {left}."


def add_timer(text):
    """Таймер: «таймер на 5 минут» (голое число — минуты)."""
    seconds = parse_duration(text)
    if seconds <= 0:
        return "На сколько минут?"
    store.add("timer", datetime.now() + timedelta(seconds=seconds), "",
              core.current_source(), duration=seconds)
    start()
    return f"Таймер на {say_duration(seconds)} запущен."


def _describe(item, now):
    due = datetime.fromisoformat(item["due"])
    if item["kind"] == "timer":
        return f"таймер, осталось {say_duration(max(1, (due - now).total_seconds()))}"
    title = "будильник" if item["kind"] == "alarm" else "напоминание"
    tail = f": {item['text']}" if item.get("text") else ""
    return f"{title} {say_moment(due, now)}{tail}"


@registry.command(
    ["какие напоминания", "мои напоминания", "список напоминаний", "покажи напоминания",
     "какие будильники", "мои будильники", "какие таймеры", "сколько осталось на таймере",
     "сколько осталось таймер", "что ты мне напомнишь", "есть напоминания",
     "какие у меня напоминания", "какие у меня будильники", "какие у меня таймеры",
     "есть будильники", "на сколько будильник", "на когда будильник", "когда будильник"],
    "Список напоминаний", "Напоминания", priority=8,
)
def list_reminders(text):
    now = datetime.now()
    kind = "alarm" if "будильник" in text else "timer" if "таймер" in text else None
    items = store.pending(kind)
    if not items:
        return {"alarm": "Будильников нет.", "timer": "Таймеров нет."}.get(kind, "Напоминаний нет.")
    lines = [f"{n}. {_describe(i, now)}" for n, i in enumerate(items[:10], 1)]
    return "\n".join(lines)


@registry.command(
    ["отмени напоминание", "удали напоминание", "отмени напоминания", "удали напоминания",
     "отмени все напоминания", "удали все напоминания", "не напоминай", "отмени будильник",
     "удали будильник", "отмени будильники", "отмени таймер", "сбрось таймер",
     "удали таймер", "останови таймер"],
    "Отменить напоминание", "Напоминания", priority=9,
)
def cancel_reminders(text):
    kind = "alarm" if "будильник" in text else "timer" if "таймер" in text else "reminder"
    items = store.pending(kind)
    if not items:
        return {"alarm": "Будильников нет.", "timer": "Таймеров нет."}.get(kind, "Напоминаний нет.")
    if kind == "timer":
        try:
            from voice import sfx
            sfx.alarm_stop()
        except Exception:
            pass
    m = re.search(r"\b(\d+)\b", text)
    if m and "все" not in text.split():
        n = int(m.group(1))
        if not 1 <= n <= len(items):
            return f"Нет пункта номер {n}."
        store.remove([items[n - 1]["id"]])
        return f"Отменил: {_describe(items[n - 1], datetime.now())}."
    store.remove([i["id"] for i in items])
    word = {"alarm": "будильники", "timer": "таймеры"}.get(kind, "напоминания")
    return f"Отменил все {word}: {len(items)}."


@registry.command(
    ["стоп будильник", "выключи будильник", "останови будильник", "хватит звенеть",
     "я проснулся", "я проснулась", "встаю", "выключи таймер", "стоп таймер",
     "стоп", "хватит"],
    "Выключить звонок будильника", "Напоминания", priority=30,
)
def stop_alarm(text):
    try:
        from voice import sfx
        ringing = sfx.alarm_stop()
    except Exception:
        ringing = False
    if ringing:
        return "Доброе утро!" if "будильник" in text or "просну" in text else "Выключил."
    if "будильник" in text:
        return "Будильник сейчас не звонит. Чтобы отменить, скажи «отмени будильник»."
    if "таймер" in text:
        return cancel_reminders("отмени таймер")
    return None   # обычное «стоп» — пусть обработает пауза музыки
