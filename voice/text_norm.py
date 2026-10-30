"""
Подготовка текста для офлайн-озвучки Silero: она молча выбрасывает цифры,
поэтому «19:13, 35%» превращаем в «девятнадцать тринадцать, тридцать пять процентов».
"""

import re

_ONES = ["ноль", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь",
         "девять", "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
         "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
_ONES_F = {1: "одна", 2: "две"}
_TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят",
         "семьдесят", "восемьдесят", "девяносто"]
_HUNDREDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот",
             "семьсот", "восемьсот", "девятьсот"]
_SCALES = [("", "", "", False), ("тысяча", "тысячи", "тысяч", True),
           ("миллион", "миллиона", "миллионов", False),
           ("миллиард", "миллиарда", "миллиардов", False)]


def plural(n, one, few, many):
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    return one if n == 1 else few if 2 <= n <= 4 else many


def _triplet(n, feminine=False):
    words = []
    h, rest = divmod(n, 100)
    if h:
        words.append(_HUNDREDS[h])
    if rest >= 20:
        t, u = divmod(rest, 10)
        words.append(_TENS[t])
        if u:
            words.append(_ONES_F[u] if feminine and u in _ONES_F else _ONES[u])
    elif rest:
        words.append(_ONES_F[rest] if feminine and rest in _ONES_F else _ONES[rest])
    return words


def number_to_words(n: int) -> str:
    if n == 0:
        return "ноль"
    words = ["минус"] if n < 0 else []
    n = abs(n)
    groups = []
    while n:
        n, g = divmod(n, 1000)
        groups.append(g)
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if not g or i >= len(_SCALES):
            continue
        one, few, many, fem = _SCALES[i]
        words += _triplet(g, feminine=fem)
        if i:
            words.append(plural(g, one, few, many))
    return " ".join(words)


def _num(m):
    return number_to_words(int(m.group(0)))


def _clock(m):
    """19:05 -> «девятнадцать ноль пять», 7:00 -> «семь ноль ноль»."""
    hours, mm = int(m.group(1)), m.group(2)
    if mm == "00":
        minutes = "ноль ноль"
    elif mm.startswith("0"):
        minutes = "ноль " + _ONES[int(mm)]
    else:
        minutes = number_to_words(int(mm))
    return f"{number_to_words(hours)} {minutes}"


def normalize_for_tts(text: str) -> str:
    t = text
    t = re.sub(r"(\d+)[.,](\d+)", lambda m: f"{number_to_words(int(m.group(1)))} и "
               f"{number_to_words(int(m.group(2)))}", t)
    t = re.sub(r"(\d+)\s*%", lambda m: f"{number_to_words(int(m.group(1)))} "
               f"{plural(int(m.group(1)), 'процент', 'процента', 'процентов')}", t)
    t = re.sub(r"(-?\d+)\s*°\s*[CС]?", lambda m: f"{number_to_words(int(m.group(1)))} "
               f"{plural(int(m.group(1)), 'градус', 'градуса', 'градусов')}", t)
    t = re.sub(r"\b(\d{1,2}):(\d{2})\b", _clock, t)
    t = re.sub(r"\d+", _num, t)
    t = t.replace("№", "номер ").replace("&", " и ")
    return " ".join(t.split())


# ---------- латиница для Silero ----------
# Silero русский не читает латиницу: раньше такой ответ уходил в gTTS — и вдруг звучал
# «старый» женский голос. Теперь переводим латиницу в русское звучание.
_WORDS_RU = {
    "youtube": "ютуб", "google": "гугл", "telegram": "телеграм", "windows": "виндоус", "vs": "вэ эс",
    "code": "код", "visual": "вижуал", "studio": "студио", "chrome": "хром", "yandex": "яндекс",
    "gigachat": "гигачат", "claude": "клод", "ok": "окей", "wifi": "вай фай", "wi": "вай", "fi": "фай",
    "bluetooth": "блютус", "enter": "энтер", "ozon": "озон", "mail": "мэйл", "ru": "ру",
    "python": "пайтон", "steam": "стим", "discord": "дискорд", "obsidian": "обсидиан",
    "blender": "блендер", "roblox": "роблокс", "minecraft": "майнкрафт", "tiktok": "тикток",
    "twitch": "твич", "spotify": "спотифай", "deepseek": "дипсик", "github": "гитхаб",
    "rutube": "рутуб", "the": "зе", "hello": "хеллоу", "jarvis": "джарвис", "phone": "фон",
    "link": "линк", "music": "мьюзик", "online": "онлайн", "player": "плеер",
    "iphone": "айфон", "android": "андроид", "samsung": "самсунг", "xiaomi": "сяоми", "apple": "эппл",
    "ngrok": "энгрок", "browser": "браузер", "edit": "эдит", "naruto": "наруто",
}
_LETTERS_RU = {"a": "эй", "b": "би", "c": "си", "d": "ди", "e": "и", "f": "эф", "g": "джи", "h": "эйч",
               "i": "ай", "j": "джей", "k": "кей", "l": "эл", "m": "эм", "n": "эн", "o": "оу", "p": "пи",
               "q": "кью", "r": "ар", "s": "эс", "t": "ти", "u": "ю", "v": "ви", "w": "дабл ю", "x": "икс",
               "y": "уай", "z": "зед"}
_DIGRAPHS = [("sch", "ш"), ("sh", "ш"), ("ch", "ч"), ("th", "т"), ("ph", "ф"), ("oo", "у"), ("ee", "и"),
             ("kh", "х"), ("zh", "ж"), ("ts", "ц"), ("ya", "я"), ("yu", "ю"), ("ck", "к"), ("qu", "кв")]
_SINGLE = str.maketrans({"a": "а", "b": "б", "c": "к", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х",
                         "i": "и", "j": "дж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п",
                         "q": "к", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "w": "в", "x": "кс",
                         "y": "и", "z": "з"})


def _latin_word(m):
    w = m.group(0)
    low = w.lower()
    if low in _WORDS_RU:
        return _WORDS_RU[low]
    if w.isupper() and len(w) <= 4:                 # «USB», «AI» — по буквам
        return " ".join(_LETTERS_RU[c] for c in low)
    for a, b in _DIGRAPHS:
        low = low.replace(a, b)
    return low.translate(_SINGLE)


def latin_to_ru(text: str) -> str:
    """«Открываю YouTube» -> «Открываю ютуб», «VS Code» -> «вэ эс код»."""
    return re.sub(r"[A-Za-z]+", _latin_word, text)
