"""
Календарь (волна 4).

Читает события из:
  • своего календаря Кеши — data/calendar.json (работает всегда);
  • Google / Яндекс по ICS-ссылке (CALENDAR_ICS_URLS в .env), включая повторяющиеся.
Пишет:
  • в свой календарь;
  • и в Яндекс Календарь по CalDAV, если заданы CALDAV_URL/USER/PASSWORD.

    «что у меня сегодня», «планы на завтра», «что в календаре на неделе»
    «добавь в календарь встречу с Петей завтра в 15:00»
"""

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import requests

from config import (CALENDAR_FILE, CALENDAR_ICS_URLS, CALDAV_URL, CALDAV_USER,
                    CALDAV_PASSWORD)
from core import registry
from timeparse import parse_when, prepare, WEEKDAY_NAMES

ICS_CACHE_SEC = 900
_ics_cache = {}
_lock = threading.RLock()
_events = None
path = CALENDAR_FILE
ics_urls = list(CALENDAR_ICS_URLS)


# ---------- свой календарь ----------
def _load():
    global _events
    if _events is None:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            _events = data if isinstance(data, list) else []
        except (OSError, ValueError):
            _events = []


def _save():
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_events, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def use_file(new_path):
    global path, _events
    with _lock:
        path, _events = new_path, None


def add_event(title, start: datetime, duration_min=60):
    item = {"id": uuid.uuid4().hex, "title": title, "start": start.isoformat(timespec="minutes"),
            "end": (start + timedelta(minutes=duration_min)).isoformat(timespec="minutes")}
    with _lock:
        _load()
        _events.append(item)
        _save()
    return item


# ---------- ICS (Google / Яндекс) ----------
def _fetch_ics(url):
    with _lock:
        hit = _ics_cache.get(url)
        if hit and time.time() - hit[0] < ICS_CACHE_SEC:
            return hit[1]
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    with _lock:
        _ics_cache[url] = (time.time(), r.content)
    return r.content


def _to_local(value):
    """date -> (datetime 00:00, весь день); datetime с зоной -> локальное время."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone().replace(tzinfo=None)
        return value, False
    return datetime(value.year, value.month, value.day), True


def ics_events(raw: bytes, start: datetime, end: datetime):
    import icalendar
    import recurring_ical_events
    cal = icalendar.Calendar.from_ical(raw)
    out = []
    for comp in recurring_ical_events.of(cal).between(start, end):
        dt, all_day = _to_local(comp.decoded("DTSTART"))
        out.append({"start": dt, "title": str(comp.get("SUMMARY", "Событие")), "all_day": all_day})
    return out


def events_between(start: datetime, end: datetime):
    with _lock:
        _load()
        local = list(_events)
    out = []
    for e in local:
        dt = datetime.fromisoformat(e["start"])
        if start <= dt < end:
            out.append({"start": dt, "title": e["title"], "all_day": False})
    for url in ics_urls:
        try:
            out += ics_events(_fetch_ics(url), start, end)
        except Exception as e:
            print(f"[agenda] не удалось прочитать календарь {url[:40]}…: {e}")
    return sorted(out, key=lambda e: e["start"])


# ---------- CalDAV (Яндекс) ----------
def _ics_for(item):
    def fmt(iso):
        return datetime.fromisoformat(iso).strftime("%Y%m%dT%H%M%S")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = item["title"].replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Kesha//RU\r\nBEGIN:VEVENT\r\n"
            f"UID:{item['id']}@kesha\r\nDTSTAMP:{stamp}\r\nDTSTART:{fmt(item['start'])}\r\n"
            f"DTEND:{fmt(item['end'])}\r\nSUMMARY:{summary}\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")


def push_caldav(item) -> bool:
    if not (CALDAV_URL and CALDAV_USER and CALDAV_PASSWORD):
        return False
    url = CALDAV_URL.rstrip("/") + f"/{item['id']}.ics"
    r = requests.put(url, data=_ics_for(item).encode("utf-8"), auth=(CALDAV_USER, CALDAV_PASSWORD),
                     headers={"Content-Type": "text/calendar; charset=utf-8", "If-None-Match": "*"},
                     timeout=15)
    r.raise_for_status()
    return True


# ---------- команды ----------
_WEEKDAY_ACC = {"понедельник": 0, "вторник": 1, "среду": 2, "четверг": 3, "пятницу": 4,
                "субботу": 5, "воскресенье": 6}


def parse_range(text, now: datetime):
    """-> (начало, конец, подпись) периода, о котором спрашивают."""
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    t = prepare(text)
    if "послезавтра" in t:
        return today + timedelta(days=2), today + timedelta(days=3), "Послезавтра"
    if "завтра" in t:
        return today + timedelta(days=1), today + timedelta(days=2), "Завтра"
    if re.search(r"\bнедел", t):
        return now, today + timedelta(days=8), "На неделе"
    for word, wd in _WEEKDAY_ACC.items():
        if re.search(rf"\b(?:в|во|на)\s+{word}\b", t):
            day = today + timedelta(days=(wd - now.weekday()) % 7)
            return day, day + timedelta(days=1), WEEKDAY_NAMES[wd].capitalize()
    return today, today + timedelta(days=1), "Сегодня"


def _line(e, multi_day):
    when = "весь день" if e["all_day"] else e["start"].strftime("%H:%M")
    if multi_day:
        when = f"{WEEKDAY_NAMES[e['start'].weekday()]} {e['start'].strftime('%d.%m')} {'' if e['all_day'] else when}".strip()
    return f"{when} — {e['title']}"


@registry.command(
    ["что у меня сегодня", "что у меня завтра", "что у меня на неделе", "что в календаре",
     "мой календарь", "покажи календарь", "планы на сегодня", "планы на завтра",
     "планы на неделю", "какие планы", "какие события", "что запланировано",
     "события на сегодня", "события на завтра", "что у меня послезавтра"],
    "Календарь: события", "Календарь", priority=6,
)
def agenda_list(text):
    now = datetime.now()
    start, end, label = parse_range(text, now)
    events = events_between(start, end)
    if not events:
        return f"{label} ничего не запланировано." if label != "На неделе" else "На неделе ничего не запланировано."
    multi = (end - start) > timedelta(days=1)
    return f"{label}: " + "; ".join(_line(e, multi) for e in events[:10]) + "."


_ADD_WORDS = ["добавь в календарь", "запиши в календарь", "внеси в календарь", "создай событие",
              "добавь событие", "запланируй", "назначь встречу"]


@registry.command(_ADD_WORDS, "Календарь: добавить событие", "Календарь", priority=8)
def agenda_add(text):
    now = datetime.now()
    when = parse_when(text, now)
    if when is None:
        return "Когда? Например: «добавь в календарь встречу завтра в 15:00»."
    title = when.rest
    for w in sorted(_ADD_WORDS, key=len, reverse=True):
        title = title.replace(w, " ")
    title = " ".join(title.split()) or ("встреча" if "встреч" in text else "событие")
    item = add_event(title, when.dt)
    synced = ""
    try:
        if push_caldav(item):
            synced = " и в Яндекс Календарь"
    except Exception as e:
        print(f"[agenda] CalDAV: {e}")
        synced = " (в Яндекс Календарь отправить не вышло)"
    day = "сегодня" if when.dt.date() == now.date() else \
        "завтра" if when.dt.date() == (now + timedelta(days=1)).date() else when.dt.strftime("%d.%m")
    return f"Добавил в календарь{synced}: {title}, {day} в {when.dt.strftime('%H:%M')}."
