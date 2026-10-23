"""
Понимание фраз (волна 2): нормализация, синонимы, нечёткий поиск.
Чистые функции без побочных эффектов — легко тестировать.
"""

import re
from collections import namedtuple
from difflib import SequenceMatcher

from config import FUZZY_THRESHOLD, FUZZY_THRESHOLD_LONG, FUZZY_MIN_LEN

_NOT_WORD = re.compile(r"[^a-zа-я0-9\- ]+")
_STRAY_HYPHEN = re.compile(r"(?<![a-zа-я0-9])-|-(?![a-zа-я0-9])")

# Фраза начинается так — это вопрос/просьба объяснить, а не команда.
# Синонимы и fuzzy тут не трогаем, пусть отвечает GigaChat.
QUESTION_STARTS = {
    "как", "что", "кто", "где", "когда", "почему", "зачем", "какой", "какая",
    "какие", "сколько", "расскажи", "объясни", "объяснишь", "почему",
}

# fuzzy ищет команду только в начале фразы: «ну вруби лампу» — да,
# «расскажи мне как-то раз про включи музыку» — нет.
FUZZY_MAX_START = 2
FUZZY_EXTRA_WORDS = 3
FUZZY_MAX_LEN_DIFF = 3
FUZZY_AMBIGUITY = 0.02

# каноническое слово -> его синонимы
SYNONYMS = {
    "включи":   "вруби врубай врубить включай включить включите",
    "выключи":  "выруби вырубай вырубить выключай выключить выключите "
                "отключи отключай потуши гаси погаси",
    "открой":   "открыть открывай откройте запускай стартани",
    "найди":    "найти найдите ищи отыщи",
    "компьютер": "комп пк ноут ноутбук компьютера",
    "свет":     "освещение",
    "громкость": "звук",
}

_SYN_MAP = {
    variant: canon
    for canon, variants in SYNONYMS.items()
    for variant in variants.split()
}
_SYN_RE = re.compile(
    r"(?<![a-zа-я0-9\-])(?:"
    + "|".join(sorted(map(re.escape, _SYN_MAP), key=len, reverse=True))
    + r")(?![a-zа-я0-9\-])"
)


def normalize(text: str) -> str:
    """Нижний регистр, ё→е, без знаков препинания, одинарные пробелы."""
    t = text.lower().replace("ё", "е")
    t = _NOT_WORD.sub(" ", t)
    t = _STRAY_HYPHEN.sub(" ", t)
    return " ".join(t.split())


def apply_synonyms(norm_text: str) -> str:
    """«вруби лампу» -> «включи лампу». Вход — уже normalize()."""
    return _SYN_RE.sub(lambda m: _SYN_MAP[m.group(0)], norm_text)


def is_question(norm_text: str) -> bool:
    words = norm_text.split()
    return bool(words) and words[0] in QUESTION_STARTS


def has_negation(norm_text: str) -> bool:
    return "не" in norm_text.split()


FuzzyHit = namedtuple("FuzzyHit", "cmd pattern score rewritten")


def _threshold(pattern_norm: str) -> float:
    return FUZZY_THRESHOLD_LONG if len(pattern_norm) >= 12 else FUZZY_THRESHOLD


def fuzzy_find(norm_text: str, commands) -> "FuzzyHit | None":
    """Найти команду, чей паттерн ПОХОЖ на кусок фразы (опечатки, искажения STT).

    Опасные команды (cmd["risky"]) не участвуют. Если два разных
    команды подходят почти одинаково — не угадываем, возвращаем None.
    rewritten — фраза, где найденный кусок заменён на точный паттерн;
    её можно отдать обычному точному матчеру.
    """
    words = norm_text.split()
    if not words:
        return None

    best_per_cmd = {}   # id(cmd) -> FuzzyHit
    for cmd in commands:
        if cmd.get("risky"):
            continue
        for raw in cmd["patterns"]:
            pn = normalize(raw)
            if len(pn) < FUZZY_MIN_LEN:
                continue
            n = len(pn.split())
            if len(words) > n + FUZZY_EXTRA_WORDS + FUZZY_MAX_START:
                continue
            limit = _threshold(pn)
            for i in range(0, min(FUZZY_MAX_START, len(words) - n) + 1):
                window = " ".join(words[i:i + n])
                if abs(len(window) - len(pn)) > FUZZY_MAX_LEN_DIFF:
                    continue
                sm = SequenceMatcher(None, window, pn)
                if sm.real_quick_ratio() < limit or sm.quick_ratio() < limit:
                    continue
                score = sm.ratio()
                if score < limit:
                    continue
                prev = best_per_cmd.get(id(cmd))
                if prev is None or score > prev.score:
                    rewritten = " ".join(words[:i] + [raw] + words[i + n:])
                    best_per_cmd[id(cmd)] = FuzzyHit(cmd, raw, score, rewritten)

    if not best_per_cmd:
        return None
    ranked = sorted(best_per_cmd.values(), key=lambda h: -h.score)
    if len(ranked) > 1 and ranked[0].score - ranked[1].score < FUZZY_AMBIGUITY:
        return None
    return ranked[0]
