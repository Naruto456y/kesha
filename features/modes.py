"""
Режимы и оформление (волны 3 и 5) — всё хранится в settings (data/settings.json).

    «тихий режим» / «говори вслух»                 — Кеша только пишет в чат
    «переключись на английский» / «...на русский»  — язык ответов и озвучки
    «мужской голос», «женский голос», «голос робота», «стандартный голос»
    «светлая тема» / «тёмная тема» / «смени тему»
    «скрой значок» / «покажи значок»              — плавающий значок реактора
    «выключи звуки» / «включи звуки»              — пики и бупы
"""

import re

import settings
from core import registry

_OFF = r"\b(выключи|отключи|отмени|убери|хватит|выйди из|сними)\b"


@registry.command(
    ["тихий режим", "молчаливый режим", "режим молчания", "молчи", "только текстом",
     "пиши в чат", "не говори вслух", "говори вслух", "говори голосом", "можешь говорить",
     "обычный режим", "отвечай голосом", "не беспокоить", "режим не беспокоить"],
    "Тихий режим (без озвучки)", "Режимы", priority=12,
)
def silent_mode(text):
    t = text.lower()
    speak = re.search(r"\bговори (вслух|голосом)\b|\bможешь говорить\b|\bобычный режим\b"
                      r"|\bотвечай голосом\b", t) and not re.search(r"\bне говори\b", t)
    if speak or (re.search(_OFF, t) and re.search(r"тих|молч|беспоко", t)):
        settings.set("silent", False)
        return "Хорошо, снова говорю вслух."
    settings.set("silent", True)
    return "Тихий режим: буду только писать в чат. Скажи «говори вслух», чтобы вернуть голос."


@registry.command(
    ["переключись на английский", "перейди на английский", "говори по английски",
     "говори по-английски", "говори на английском", "отвечай на английском",
     "английский режим", "switch to english", "speak english",
     "переключись на русский", "перейди на русский", "говори по русски", "говори по-русски",
     "говори на русском", "отвечай на русском", "switch to russian", "speak russian"],
    "Язык ответов", "Режимы", priority=12,
)
def switch_language(text):
    if re.search(r"англ|english", text.lower()):
        settings.set("language", "en")
        return "Switched to English. Say «переключись на русский» to switch back."
    settings.set("language", "ru")
    return "Перешёл на русский."


_VOICE_NAMES = {"google": "стандартный", "female": "женский", "male": "мужской", "robot": "робот"}


@registry.command(
    ["смени голос", "поменяй голос", "другой голос", "мужской голос", "женский голос",
     "голос робота", "робот голос", "голосом робота", "стандартный голос", "обычный голос",
     "голос гугл", "какой у тебя голос", "говори мужским голосом", "говори женским голосом"],
    "Сменить голос", "Режимы", priority=12,
)
def switch_voice(text):
    t = text.lower()
    if "какой у тебя голос" in t:
        return f"Сейчас голос: {_VOICE_NAMES.get(settings.get('voice'), 'стандартный')}."
    if "мужск" in t:
        voice = "male"
    elif "женск" in t:
        voice = "female"
    elif "робот" in t:
        voice = "robot"
    elif re.search(r"стандарт|обычн|гугл|google", t):
        voice = "google"
    else:   # «смени голос» — следующий по кругу
        order = list(_VOICE_NAMES)
        voice = order[(order.index(settings.get("voice")) + 1) % len(order)]
    settings.set("voice", voice)
    return f"Теперь голос: {_VOICE_NAMES[voice]}."


@registry.command(
    ["светлая тема", "светлую тему", "темная тема", "тёмная тема", "темную тему", "тёмную тему",
     "смени тему", "поменяй тему", "другая тема", "ночная тема", "дневная тема"],
    "Тема оформления", "Режимы", priority=12,
)
def switch_theme(text):
    t = text.lower().replace("ё", "е")
    if re.search(r"светл|дневн", t):
        theme = "light"
    elif re.search(r"темн|ночн", t):
        theme = "dark"
    else:
        theme = "light" if settings.get("theme") == "dark" else "dark"
    settings.set("theme", theme)
    return "Светлая тема включена." if theme == "light" else "Тёмная тема включена."


@registry.command(
    ["скрой значок", "убери значок", "спрячь значок", "покажи значок", "верни значок",
     "плавающий значок", "значок реактора"],
    "Плавающий значок", "Режимы", priority=12,
)
def floating_icon(text):
    show = not re.search(r"\b(скрой|убери|спрячь|выключи)\b", text.lower())
    settings.set("floating_icon", show)
    return "Значок на экране." if show else "Значок скрыт. Скажи «покажи значок», чтобы вернуть."


@registry.command(
    ["выключи звуки", "отключи звуки", "без звуков", "включи звуки", "верни звуки",
     "звуковые эффекты"],
    "Звуковые эффекты", "Режимы", priority=12,
    risky=True,   # только точной фразой: GigaChat однажды сделал из «не видно что-то откл» «выключи звуки»
)
def sounds_toggle(text):
    on = not re.search(r"\b(выключи|отключи|без)\b", text.lower())
    settings.set("sounds", on)
    return "Звуки включены." if on else "Звуки выключены."
