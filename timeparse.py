"""
Разбор времени и чисел по-русски (волна 4) — для напоминаний, будильника,
таймера и календаря. Чистые функции: «сейчас» передаётся параметром.

    words_to_digits("через двадцать пять минут")   -> "через 25 минут"
    parse_duration("таймер на полтора часа")        -> 5400
    parse_when("напомни завтра в 7 вечера позвонить маме", now)
        -> When(dt=<завтра 19:00>, rest="напомни позвонить маме")
"""

import re
from collections import namedtuple
from datetime import datetime, timedelta

# ---------- числа словами ----------
_UNITS = {
    "ноль": 0, "один": 1, "одна": 1, "одну": 1, "одно": 1, "два": 2, "две": 2,
    "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8,
    "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12,
    "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16,
    "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19,
}
_TENS = {"двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50,
         "шестьдесят": 60, "семьдесят": 70, "восемьдесят": 80, "девяносто": 90}
_HUNDREDS = {"сто": 100, "двести": 200, "триста": 300, "четыреста": 400,
             "пятьсот": 500, "шестьсот": 600, "семьсот": 700, "восемьсот": 800,
             "девятьсот": 900}
_THOUSAND = {"тысяча", "тысячи", "тысяч", "тысячу"}
_NUM_WORDS = {**_UNITS, **_TENS, **_HUNDREDS}


def _rank(value: int) -> int:
    """Разряд слова: 3 — сотни, 2 — десятки, 1 — единицы (10–19 занимают оба)."""
    if value >= 100:
        return 3
    if value >= 20:
        return 2
    return 1


def words_to_digits(text: str) -> str:
    """Заменить числа словами на цифры: «сто двадцать пять» -> «125».
    Склеиваем только по правилам: «семь тридцать» — это 7 и 30, а не 37."""
    out = []
    total = group = 0
    last_rank = 4          # разряд последнего слова в группе
    teen = False           # 10–19 занимают и десятки, и единицы
    in_num = False

    def flush():
        nonlocal total, group, last_rank, teen, in_num
        if in_num:
            out.append(str(total + group))
        total = group = 0
        last_rank, teen, in_num = 4, False, False

    for tok in text.split(" "):
        w = tok.lower().replace("ё", "е")
        if w in _NUM_WORDS:
            value = _NUM_WORDS[w]
            rank = _rank(value)
            if in_num and (rank >= last_rank or teen):
                flush()
            group += value
            last_rank, teen, in_num = rank, 10 <= value <= 19, True
        elif w in _THOUSAND and (in_num or w == "тысяча"):
            total += (group or 1) * 1000
            group, last_rank, teen, in_num = 0, 4, False, True
        else:
            flush()
            out.append(tok)
    flush()
    return " ".join(out)


def prepare(text: str) -> str:
    """Нижний регистр, ё→е, числа цифрами, без знаков (кроме «:» во времени)."""
    t = text.lower().replace("ё", "е")
    t = re.sub(r"(?<=\d)[.](?=\d\d\b)", ":", t)            # 18.30 -> 18:30
    t = re.sub(r"[^\w:\s-]+|(?<!\d):|:(?!\d)", " ", t)
    return words_to_digits(" ".join(t.split()))


# ---------- длительности ----------
_UNIT_SEC = [
    (r"сек\w*", 1), (r"мин\w*", 60), (r"час(?:а|ов|ик)?", 3600),
    (r"(?:день|дня|дней|сутки|суток)", 86400), (r"недел\w*", 7 * 86400),
]
_UNIT_RE = "|".join(f"(?:{u})" for u, _ in _UNIT_SEC)
_COMPONENT = rf"(?:(?:\d+|полтора|полторы|пол)\s*)?(?:{_UNIT_RE})"
_DURATION_RE = re.compile(rf"\b(?:полчаса|{_COMPONENT})(?:\s+(?:и\s+)?{_COMPONENT})*\b")


def _unit_seconds(unit: str) -> int:
    for pattern, sec in _UNIT_SEC:
        if re.fullmatch(pattern, unit):
            return sec
    return 0


def _duration_value(span: str) -> int:
    if span == "полчаса":
        return 1800
    total = 0
    for m in re.finditer(rf"(\d+|полтора|полторы|пол)?\s*({_UNIT_RE})", span):
        count, unit = m.group(1), m.group(2)
        sec = _unit_seconds(unit)
        if count in ("полтора", "полторы"):
            total += int(sec * 1.5)
        elif count == "пол":
            total += sec // 2
        else:
            total += sec * (int(count) if count else 1)
    return total


def find_duration(prepared: str):
    """-> (секунды, start, end) первой длительности в тексте или None."""
    for m in _DURATION_RE.finditer(prepared):
        sec = _duration_value(m.group(0))
        if sec:
            return sec, m.start(), m.end()
    return None


def parse_duration(text: str, default_unit: int = 60) -> int:
    """«5 минут» -> 300, «полтора часа» -> 5400, «5» -> 300 (голое число — минуты)."""
    t = prepare(text)
    found = find_duration(t)
    if found:
        return found[0]
    m = re.search(r"\b(\d+)\b", t)
    return int(m.group(1)) * default_unit if m else 0


# ---------- момент времени ----------
When = namedtuple("When", "dt rest")

_WEEKDAYS = {"понедельник": 0, "вторник": 1, "среду": 2, "среда": 2, "четверг": 3,
             "пятницу": 4, "пятница": 4, "субботу": 5, "суббота": 5,
             "воскресенье": 6}
_DAY_WORDS = {"сегодня": 0, "завтра": 1, "послезавтра": 2}
_PART_DEFAULT = {"утром": 9, "днем": 14, "вечером": 19, "ночью": 23}

_RELATIVE_RE = re.compile(rf"\bчерез\s+(?P<d>полчаса|{_COMPONENT}(?:\s+(?:и\s+)?{_COMPONENT})*)\b")
_DAY_RE = re.compile(r"\b(?:послезавтра|завтра|сегодня)\b")
_WEEKDAY_RE = re.compile(r"\b(?:в|во)\s+(?:следующ\w+\s+)?(" + "|".join(_WEEKDAYS) + r")\b")
_TIME_RES = [
    # в 18:30 / на 7:05 / к 9:00
    re.compile(r"\b(?:в|на|к)\s+(?P<h>\d{1,2}):(?P<m>\d{2})(?:\s+(?P<p>утра|дня|вечера|ночи))?\b"),
    # в 7 часов 30 минут (утра)
    re.compile(r"\b(?:в|на|к)\s+(?P<h>\d{1,2})\s+час\w*\s+(?P<m>\d{1,2})\s+минут\w*"
               r"(?:\s+(?P<p>утра|дня|вечера|ночи))?"),
    # в 18 30
    re.compile(r"\b(?:в|на|к)\s+(?P<h>\d{1,2})\s+(?P<m>\d{2})\b(?!\s*(?:минут|сек|час))"),
    # в 7 (часов) (вечера)
    re.compile(r"\b(?:в|на|к)\s+(?P<h>\d{1,2})(?:\s+час(?:а|ов)?)?(?:\s+(?P<p>утра|дня|вечера|ночи))?\b"
               r"(?!\s*(?:минут|сек|:))"),
]
_SPECIAL_RE = re.compile(r"\b(?:в|к)\s+(полдень|полночь)\b")
_PART_RE = re.compile(r"\b(утром|днем|вечером|ночью)\b")


def _cut(text, start, end):
    return text[:start] + " " + text[end:]


def _apply_part(hour, part):
    if part in ("дня", "вечера") and hour < 12:
        return hour + 12
    if part == "ночи" and hour == 12:
        return 0
    if part == "утра" and hour == 12:
        return 0
    return hour


def parse_when(text: str, now: datetime, prefer_morning: bool = False) -> "When | None":
    """Найти момент времени во фразе. rest — фраза без слов о времени.
    prefer_morning — для будильника: «разбуди в 7» значит 7 утра, а не вечера."""
    t = prepare(text)

    m = _RELATIVE_RE.search(t)
    if m:
        sec = _duration_value(m.group("d"))
        if sec:
            return When(now + timedelta(seconds=sec), " ".join(_cut(t, *m.span()).split()))

    day_offset = None
    m = _DAY_RE.search(t)
    if m:
        day_offset = _DAY_WORDS[m.group(0)]
        t = _cut(t, *m.span())
    else:
        m = _WEEKDAY_RE.search(t)
        if m:
            wd = _WEEKDAYS[m.group(1)]
            day_offset = (wd - now.weekday()) % 7 or 7
            t = _cut(t, *m.span())

    hour = minute = None
    part_given = False
    m = _SPECIAL_RE.search(t)
    if m:
        hour, minute = (12, 0) if m.group(1) == "полдень" else (0, 0)
        part_given = True
        t = _cut(t, *m.span())
    else:
        for rx in _TIME_RES:
            m = rx.search(t)
            if not m:
                continue
            h = int(m.group("h"))
            mi = int(m.groupdict().get("m") or 0)
            part = m.groupdict().get("p")
            if h > 24 or mi > 59:
                continue
            hour, minute = _apply_part(h % 24, part), mi
            part_given = bool(part) or h >= 13 or h == 0 or ":" in m.group(0)
            t = _cut(t, *m.span())
            break
    m = _PART_RE.search(t)
    if m:
        if hour is None:
            hour, minute, part_given = _PART_DEFAULT[m.group(1)], 0, True
        elif m.group(1) in ("вечером", "днем") and hour < 12:
            hour, part_given = hour + 12, True
        else:
            part_given = True
        t = _cut(t, *m.span())

    rest = " ".join(t.split())
    if hour is None and day_offset is None:
        return None
    if hour is None:
        hour, minute = 9, 0                     # «напомни завтра» -> завтра в 9:00

    base = now.replace(second=0, microsecond=0)
    if day_offset is not None:
        day = base + timedelta(days=day_offset)
        return When(day.replace(hour=hour, minute=minute), rest)

    # день не назван: ближайшее будущее; «в 6» днём — это скорее 18:00
    candidates = [hour] if part_given or hour >= 12 or prefer_morning else [hour, hour + 12]
    options = []
    for h in candidates:
        dt = base.replace(hour=h, minute=minute)
        if dt <= now:
            dt += timedelta(days=1)
        options.append(dt)
    return When(min(options), rest)


# ---------- озвучка ----------
def _plural(n, one, few, many):
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    return one if n == 1 else few if 2 <= n <= 4 else many


def say_duration(seconds: int) -> str:
    """5400 -> «1 час 30 минут»."""
    seconds = int(round(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} {_plural(days, 'день', 'дня', 'дней')}")
    if hours:
        parts.append(f"{hours} {_plural(hours, 'час', 'часа', 'часов')}")
    if minutes:
        parts.append(f"{minutes} {_plural(minutes, 'минуту', 'минуты', 'минут')}")
    if secs and not days and not hours:
        parts.append(f"{secs} {_plural(secs, 'секунду', 'секунды', 'секунд')}")
    return " ".join(parts) or "0 секунд"


_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
           "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAY_NAMES = ["понедельник", "вторник", "среда", "четверг", "пятница",
                 "суббота", "воскресенье"]


def say_moment(dt: datetime, now: datetime) -> str:
    """-> «сегодня в 18:30», «завтра в 07:00», «25 октября в 09:00»."""
    days = (dt.date() - now.date()).days
    clock = dt.strftime("%H:%M")
    if days == 0:
        return f"сегодня в {clock}"
    if days == 1:
        return f"завтра в {clock}"
    if days == 2:
        return f"послезавтра в {clock}"
    return f"{dt.day} {_MONTHS[dt.month - 1]} в {clock}"


plural = _plural
