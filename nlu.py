"""
Понимание фраз (волна 2): нормализация, синонимы, нечёткий поиск.
Чистые функции без побочных эффектов — легко тестировать.
"""

import re
from functools import lru_cache
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
FUZZY_AMBIGUITY = 0.25   # в «буквах» _weight: почти поровну — не угадываем
# каждое слово окна должно быть похоже на своё слово паттерна: иначе «сделай так»
# набирает 0.82 с «сделай фотку» только за счёт первого слова
FUZZY_WORD_MIN = 0.7
# паттерн из одного слова ищем только в начале или после этих слов: иначе
# «очисти кэш браузера» по слову «браузер» открывала браузер
FUZZY_LEAD_FILLERS = {"ну", "а", "давай", "слушай", "пожалуйста", "эй", "так"}

# каноническое слово -> его синонимы
SYNONYMS = {
    "включи":   "вруби врубай врубить включай включить включите включишь включаешь врубишь",
    "выключи":  "выруби вырубай вырубить выключай выключить выключите выключишь вырубишь "
                "отключи отключай потуши гаси погаси выключайте",
    "открой":   "открыть открывай откройте запускай стартани откроешь открываешь откройка",
    "найди":    "найти найдите ищи отыщи найдешь найдёшь поищешь отыщешь",
    "покажи":   "показать покажите покажешь глянь",
    "сделай":   "сделать сделайте сделаешь",
    "поставь":  "поставить поставьте поставишь",
    "музыку":   "музон музончик музло музычку песенки",
    "громче":   "громчей погромчей громчее",
    "тише":     "тишей потишей",
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


# GigaAM иногда мешает алфавиты в одном слове: «youтube», «telegрam».
_LOOKALIKE = str.maketrans({"а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h", "о": "o",
                            "р": "p", "с": "c", "т": "t", "у": "y", "х": "x", "ь": "b",
                            "ю": "y"})   # «юoutube» -> «youtube»
# обратно: «музыкy» (латинская y) -> «музыку»
_TO_CYR = str.maketrans({"a": "а", "b": "в", "e": "е", "k": "к", "m": "м", "h": "н", "o": "о",
                         "p": "р", "c": "с", "t": "т", "y": "у", "x": "х"})
_LATIN = re.compile(r"[a-z]")
_CYRILLIC = re.compile(r"[а-яё]")


def fix_mixed_script(text: str) -> str:
    """В слове есть и латиница, и кириллица -> приводим к алфавиту, которого больше:
    «youтube» -> «youtube», «музыкy» -> «музыку». Чистые слова не трогаем."""
    def fix(m):
        low = m.group(0).lower()
        lat, cyr = len(_LATIN.findall(low)), len(_CYRILLIC.findall(low))
        if not (lat and cyr):
            return m.group(0)
        if cyr > lat and all(ch in "abekmhopctyx" for ch in _LATIN.findall(low)):
            return low.translate(_TO_CYR)
        return low.translate(_LOOKALIKE)
    return re.sub(r"[A-Za-zА-Яа-яЁё]+", fix, text)


def apply_synonyms(norm_text: str) -> str:
    """«вруби лампу» -> «включи лампу». Вход — уже normalize()."""
    return _SYN_RE.sub(lambda m: _SYN_MAP[m.group(0)], norm_text)


def is_question(norm_text: str) -> bool:
    words = norm_text.split()
    return bool(words) and words[0] in QUESTION_STARTS


def has_negation(norm_text: str) -> bool:
    return "не" in norm_text.split()


def has_latin(text: str) -> bool:
    """Текст в основном латиницей (английский)."""
    letters = re.findall(r"[a-zA-Zа-яА-ЯёЁ]", text)
    latin = sum(1 for ch in letters if ch.isascii())
    return bool(letters) and latin / len(letters) > 0.3


FuzzyHit = namedtuple("FuzzyHit", "cmd pattern score rewritten")


def _word_close(w: str, p: str) -> bool:
    """Слово похоже на слово паттерна. Короткие «кок»/«как», «чдо»/«что» — одна буква на 3
    даёт ratio 0.67, поэтому для слов той же длины от 3 букв прощаем одну замену."""
    if w == p or SequenceMatcher(None, w, p).ratio() >= FUZZY_WORD_MIN:
        return True
    return len(w) == len(p) >= 3 and sum(a != b for a, b in zip(w, p)) == 1


def _weight(window: str, pattern: str, score: float) -> float:
    """Совпавшие буквы минус несовпавшие (пополам): длинный паттерн почти целиком
    («пиреведи на английский язык» -> translate_en) важнее точного куска («на английский»),
    но лишние буквы («выключи лампу» для «включе лампу») штрафуются."""
    return (len(window) + len(pattern)) / 2 * (2 * score - 1)


@lru_cache(maxsize=None)
def _norm_pattern(raw: str) -> str:
    """normalize() паттерна — один раз: fuzzy перебирает их сотни на каждую фразу."""
    return normalize(raw)


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
            pn = _norm_pattern(raw)
            if len(pn) < FUZZY_MIN_LEN:
                continue
            n = len(pn.split())
            if len(words) > n + FUZZY_EXTRA_WORDS + FUZZY_MAX_START:
                continue
            limit = _threshold(pn)
            for i in range(0, min(FUZZY_MAX_START, len(words) - n) + 1):
                if n == 1 and not all(w in FUZZY_LEAD_FILLERS for w in words[:i]):
                    continue
                window = " ".join(words[i:i + n])
                if abs(len(window) - len(pn)) > FUZZY_MAX_LEN_DIFF:
                    continue
                sm = SequenceMatcher(None, window, pn)
                # одно слово из 5–6 букв с одной заменой («квист», «дипси» -> «депси») — ratio 0.8,
                # ниже порога, но это типичная ошибка STT
                one_sub = n == 1 and len(window) == len(pn) >= 5 and \
                    sum(a != b for a, b in zip(window, pn)) == 1
                if not one_sub and (sm.real_quick_ratio() < limit or sm.quick_ratio() < limit):
                    continue
                score = sm.ratio()
                if score < limit and not one_sub:
                    continue
                if not all(_word_close(w, p) for w, p in zip(words[i:i + n], pn.split())):
                    continue
                weight = _weight(window, pn, score)
                prev = best_per_cmd.get(id(cmd))
                if prev is None or weight > prev[0]:
                    rewritten = " ".join(words[:i] + [raw] + words[i + n:])
                    best_per_cmd[id(cmd)] = (weight, FuzzyHit(cmd, raw, score, rewritten))

    if not best_per_cmd:
        return None
    ranked = sorted(best_per_cmd.values(), key=lambda wh: -wh[0])
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < FUZZY_AMBIGUITY:
        return None
    return ranked[0][1]
