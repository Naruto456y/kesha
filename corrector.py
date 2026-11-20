"""
Единый слой исправления услышанного: STT ошибается одинаково («лапму», «вкладочка»,
«psidion»), поэтому Кеша запоминает такие ошибки и чинит их сама, без GigaChat.

Правила лежат в data/corrections.json:
    words    «лапму» -> «лампу»                    слово где угодно во фразе
    phrases  «новая вкладочка» -> «новая вкладка»  фраза целиком
    candidates  пары, замеченные пока один раз

Откуда берутся правила:
  1. Не поняла фразу, а следующую (похожую) в течение 20 с поняла — значит, ты повторил
     то же самое внятнее. Пара записывается кандидатом.
  2. GigaChat исправил фразу в команду — та же пара.
  3. Пара встретилась LEARN_AFTER раз — становится правилом и работает мгновенно.
  4. Голосом: «когда я говорю икс, это значит игрек» — правило сразу (features/learning.py).

Слово не станет «ошибкой», если оно есть в словаре команд: иначе «включи свет» ->
«выключи свет» выучилось бы как замена «включи» на «выключи».
"""
import json
import os
import re
import threading
import time

from rapidfuzz import fuzz

from config import DATA_DIR

FILE = DATA_DIR / "corrections.json"
LEARN_AFTER = 2            # столько раз увидеть пару, чтобы она стала правилом
REPEAT_WINDOW = 20.0       # с: «не поняла» -> «поняла» считаем повтором той же просьбы
PHRASE_MIN_RATIO = 60      # похожесть фраз (0..100), ниже — это была другая просьба
WORD_MIN_RATIO = 50        # похожесть заменяемого слова на правильное
MAX_WORDS = 6              # длиннее — не команда, а разговор
MAX_CANDIDATES = 300

_lock = threading.RLock()
_data = None
_regex = None              # собранное выражение для words
_pending = {}              # источник -> (фраза, время): последняя непонятая
path = FILE
vocab = lambda: set()      # noqa: E731 — слова команд; задаёт core


def use_file(p):
    """Тесты: своя база правил."""
    global path, _data, _regex
    with _lock:
        path, _data, _regex = p, None, None
        _pending.clear()


def _norm(text: str) -> str:
    t = (text or "").lower().replace("ё", "е")
    t = re.sub(r"[^a-zа-я0-9\- ]+", " ", t)
    return " ".join(t.split())


def _load():
    global _data
    if _data is not None:
        return
    try:
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
    except (OSError, ValueError):
        loaded = {}
    _data = {"words": dict(loaded.get("words", {})), "phrases": dict(loaded.get("phrases", {})),
             "candidates": dict(loaded.get("candidates", {}))}


def _save():
    global _regex
    _regex = None
    try:
        os.makedirs(os.path.dirname(str(path)), exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_data, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except OSError as e:
        print(f"[corrector] не сохранил правила: {e}")


def _words_regex():
    global _regex
    if _regex is None:
        keys = sorted(_data["words"], key=len, reverse=True)
        _regex = re.compile(r"(?<![\w-])(?:" + "|".join(map(re.escape, keys)) + r")(?![\w-])") if keys else False
    return _regex


def apply(text: str) -> str:
    """Исправить фразу по выученным правилам. Без правил возвращает текст как есть."""
    if not text:
        return text
    with _lock:
        _load()
        if not _data["words"] and not _data["phrases"]:
            return text
        fixed = _data["phrases"].get(_norm(text))
        if fixed:
            return fixed
        rx = _words_regex()
        if not rx:
            return text
        low = text.lower().replace("ё", "е")
        return rx.sub(lambda m: _data["words"][m.group(0)], low) if rx.search(low) else text


def rules() -> dict:
    with _lock:
        _load()
        return {"words": dict(_data["words"]), "phrases": dict(_data["phrases"])}


def teach(wrong: str, right: str) -> bool:
    """Правило сразу, без испытательного срока (сказал человек)."""
    wrong, right = _norm(wrong), _norm(right)
    if not wrong or not right or wrong == right:
        return False
    with _lock:
        _load()
        kind = "words" if " " not in wrong else "phrases"
        _data[kind][wrong] = right
        _data["candidates"] = {k: v for k, v in _data["candidates"].items() if not k.startswith(wrong + "\t")}
        _save()
    return True


def forget(wrong: str) -> bool:
    """Убрать правило: по неправильному или по правильному варианту."""
    key = _norm(wrong)
    if not key:
        return False
    with _lock:
        _load()
        hit = False
        for kind in ("words", "phrases"):
            for w in [w for w, r in _data[kind].items() if key in (w, r)]:
                del _data[kind][w]
                hit = True
        if hit:
            _save()
        return hit


def _pair(heard: str, right: str):
    """(вид, неправильно, правильно) или None, если это не исправление."""
    a, b = _norm(heard), _norm(right)
    if not a or not b or a == b or len(a.split()) > MAX_WORDS:
        return None
    wa, wb = a.split(), b.split()
    if len(wa) == len(wb):
        diff = [(x, y) for x, y in zip(wa, wb) if x != y]
        if len(diff) == 1:
            x, y = diff[0]
            if len(x) >= 3 and x not in vocab() and fuzz.ratio(x, y) >= WORD_MIN_RATIO:
                return "words", x, y
            if x in vocab():
                return None        # настоящее слово команды — это была другая команда
    if fuzz.ratio(a, b) < PHRASE_MIN_RATIO:
        return None
    return "phrases", a, b


def note_fix(heard: str, right: str) -> bool:
    """Замечена пара «услышано -> имелось в виду». True — пара стала правилом."""
    pair = _pair(heard, right)
    if pair is None:
        return False
    kind, wrong, good = pair
    with _lock:
        _load()
        if _data[kind].get(wrong) == good:
            return False
        key = f"{wrong}\t{good}"
        n = _data["candidates"].get(key, 0) + 1
        if n >= LEARN_AFTER:
            _data["candidates"].pop(key, None)
            _data[kind][wrong] = good
            _save()
            return True
        if len(_data["candidates"]) >= MAX_CANDIDATES:
            _data["candidates"].pop(next(iter(_data["candidates"])))
        _data["candidates"][key] = n
        _save()
    return False


def note_failure(source: str, text: str):
    """Фразу локально не поняли."""
    if text and len(_norm(text).split()) <= MAX_WORDS:
        _pending[source] = (text, time.time())


def note_success(source: str, text: str) -> bool:
    """Фразу поняли. Если прямо перед ней была похожая непонятая — это повтор. True — выучено правило."""
    last = _pending.pop(source, None)
    if not last or time.time() - last[1] > REPEAT_WINDOW:
        return False
    return note_fix(last[0], text)
