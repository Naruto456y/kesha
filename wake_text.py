"""
Слово «Кеша» в распознанном тексте — по целым словам, а не подстрокой.

Раньше «кеш» искался подстрокой: «очисти кэш браузера» будил Кешу и превращался
в «очисти браузера», «кешбэк» — в «бэк», а «Кеша» с большой буквы (Aqua) не находилась.

Правила:
- WAKE_WORDS длиной от 4 букв («кеша», «гоша») и формы «кеши/кешу/...» — в любом месте фразы;
- короткие («кеш», «кэш»), алиасы из config и слова на 1 букву от «кеша» — только
  в начале фразы (можно после «ну», «эй», «слушай»): «каша на завтрак» Кешу не будит.
"""
import re

from config import WAKE_WORDS, WAKE_ALIASES

_WORD = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:-[A-Za-zА-Яа-яЁё]+)*")
FILLERS = {"ну", "эй", "слушай", "привет", "алло", "а", "о", "хей", "так", "окей", "ок"}
FORMS = {"кеша", "кеши", "кеше", "кешу", "кешей", "кешенька", "кешка", "кешечка"}
# на 1 букву от «кеша», но это другие слова — их не считаем
NOT_WAKE = {"леша", "наша", "ваша", "каши", "кеды", "кета"}

_STRONG = {w for w in WAKE_WORDS if len(w) >= 4} | FORMS
_WEAK = {w for w in WAKE_WORDS if len(w) < 4} | set(WAKE_ALIASES)


def _norm(word):
    return word.lower().replace("ё", "е")


def _one_edit(a, b):
    """Расстояние Левенштейна между a и b не больше 1."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    if len(a) == len(b):
        return a[i + 1:] == b[i + 1:]
    return a[i:] == b[i + 1:]


def _like_kesha(w):
    return 3 <= len(w) <= 6 and w not in NOT_WAKE and w[0] in "кгхб" and _one_edit(w, "кеша")


def find_wake(text, strong_only=False):
    """-> список (start, end) слов-активаторов в исходном тексте.
    strong_only — только настоящие «Кеша»/«Гоша» (алиасы фон даёт слишком часто)."""
    words = list(_WORD.finditer(text or ""))
    spans = []
    for i, m in enumerate(words):
        w = _norm(m.group(0))
        at_start = i == 0 or (i == 1 and _norm(words[0].group(0)) in FILLERS)
        if w in _STRONG or (not strong_only and at_start and (w in _WEAK or _like_kesha(w))):
            spans.append((m.start(), m.end()))
    return spans


def has_wake(text) -> bool:
    return bool(find_wake(text))


def strip_wake(text) -> str:
    """Убрать слова-активаторы (и «ну/эй» перед ними), знаки препинания на конце не трогаем."""
    spans = find_wake(text)
    if not spans:
        return (text or "").strip()
    first = _WORD.match(text.lstrip())
    lead = len(text) - len(text.lstrip())
    if first and _norm(first.group(0)) in FILLERS and spans[0][0] > lead:
        spans[0] = (lead, spans[0][1])
    out, pos = [], 0
    for a, b in spans:
        out.append(text[pos:a])
        pos = b
    out.append(text[pos:])
    t = re.sub(r"\s+([,.!?:;])", r"\1", " ".join("".join(out).split()))
    t = re.sub(r"([,.!?:;])(?:\s*[,.!?:;])+", r"\1", t)   # «, ,» после выреза слова
    return t.strip().lstrip(" ,.!?:;-").rstrip(" ,")


def from_last_wake(text) -> str:
    """Текст с последнего слова-активатора (для записи поверх видео/ТВ)."""
    spans = find_wake(text, strong_only=True)
    return text[spans[-1][0]:] if spans else ""


# имена, которые на 2 буквы от «кеша» — их не принимаем даже при уверенной акустике
_NAMES = {"леша", "даша", "паша", "маша", "яша", "миша", "саша", "наташа", "гоша", "лиза", "кира", "кишка", "каши"}


def _edits(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def near_kesha(text) -> bool:
    """Мягкая проверка для второй ступени wake word: короткая фраза, первое слово
    на 2 буквы от «кеша» («тише», «меше» — так GigaAM слышит быстрое «Кеша»)."""
    words = [_norm(m.group(0)) for m in _WORD.finditer(text or "")]
    return 0 < len(words) <= 2 and words[0] not in _NAMES and 3 <= len(words[0]) <= 6         and _edits(words[0], "кеша") <= 2


# «Алиса, включи музыку» — это колонке, а не Кеше: такую фразу Кеша не выполняет
OTHER_ASSISTANTS = {"алиса", "алис", "алису", "алисы", "алисочка", "алиска", "маруся", "марусь",
                    "сири", "siri", "алекса", "alexa", "салют", "сбер", "джой", "afina", "афина"}


def addressed_to_other(text) -> bool:
    """Фраза обращена к другому помощнику: первое слово (после «ну», «эй») — его имя."""
    for w in re.findall(r"[\w-]+", (text or "").lower().replace("ё", "е")):
        if w not in FILLERS:
            return w in OTHER_ASSISTANTS
    return False
