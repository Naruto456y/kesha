"""Каждая команда: свои паттерны ловит точно, а опечатки STT («пагода», «кок дела», «квист»)
узнаёт через fuzzy хотя бы в 70% случаев. Опасные (risky) — только точно, без fuzzy."""
import pytest

import commands  # noqa: F401 — регистрирует команды
import core
from config import FUZZY_MIN_LEN
from nlu import fuzzy_find, normalize

PASS_THROUGH = {"open_app", "stop_alarm", "translate_free"}   # отдают None, если фраза не их
FUZZY_MIN_SHARE = 0.7

# типичные ошибки GigaAM: аканье, е/и, глухие/звонкие, мягкий знак, обрезанный конец слова
SWAPS = [("о", "а"), ("е", "и"), ("а", "о"), ("и", "е"), ("ш", "щ"), ("з", "с"), ("т", "д"), ("ь", "")]

ALL = core.registry.commands
ALL_PATTERNS = {normalize(p) for c in ALL for p in c["patterns"]}


def typos(pattern):
    out = set()
    for a, b in SWAPS:
        i = pattern.find(a)
        if i >= 0:
            out.add(pattern[:i] + b + pattern[i + 1:])
    longest = max(pattern.split(), key=len)
    if len(longest) > 4:
        out.add(pattern.replace(longest, longest[:-1], 1))
    return sorted(v for v in out if v != pattern and v not in ALL_PATTERNS)


def cases(cmd):
    return [v for p in cmd["patterns"] if len(normalize(p)) >= FUZZY_MIN_LEN for v in typos(normalize(p))]


def _ids(cmds):
    return [c["name"] for c in cmds]


@pytest.mark.parametrize("cmd", ALL, ids=_ids(ALL))
def test_patterns_route_to_own_command(cmd):
    for p in cmd["patterns"]:
        first = next(m for m in core._matching(p)
                     if m["name"] not in PASS_THROUGH or m["name"] == cmd["name"])
        assert first["name"] == cmd["name"], (p, first["name"])


SAFE = [c for c in ALL if not c.get("risky") and cases(c)]


@pytest.mark.parametrize("cmd", SAFE, ids=_ids(SAFE))
def test_fuzzy_typos_per_command(cmd):
    variants = cases(cmd)
    missed = [(v, h.cmd["name"] if h else None) for v in variants
              if not ((h := fuzzy_find(v, ALL)) and h.cmd["name"] == cmd["name"])]
    share = 1 - len(missed) / len(variants)
    assert share >= FUZZY_MIN_SHARE, f"{share:.0%}, мимо: {missed[:6]}"


RISKY = [c for c in ALL if c.get("risky") and cases(c)]


@pytest.mark.parametrize("cmd", RISKY, ids=_ids(RISKY))
def test_risky_never_fuzzy(cmd):
    """Выключение ПК, Bluetooth, звонок: опечатка не должна их запускать."""
    for v in cases(cmd):
        hit = fuzzy_find(v, ALL)
        assert not hit or hit.cmd["name"] != cmd["name"], v


@pytest.mark.parametrize("text", [
    "я сегодня ходил в школу", "мама приготовила ужин", "давай посмотрим видео потом",
    "он сказал что придёт позже", "какой красивый закат", "очисти кэш браузера",
    "на завтрак была каша", "кушать хочу", "привет как у тебя там погодка в москве у бабушки",
])
def test_background_speech_not_fuzzy(text):
    hit = fuzzy_find(normalize(text), ALL)
    assert hit is None, (text, hit and hit.cmd["name"], hit and hit.pattern)
