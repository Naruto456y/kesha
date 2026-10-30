"""
Мелкие полезные команды без интернета и ключей (волна 6).

    «сколько будет 25 умножить на 4», «корень из 144», «15 процентов от 2000»
    «подбрось монетку», «кинь кубик», «случайное число от 1 до 100»
    «повтори», «что ты умеешь», «расскажи анекдот»
    «нагрузка компьютера», «есть ли интернет»
    «сколько дней до нового года», «сколько дней до 1 сентября»
    «запусти секундомер» / «сколько на секундомере» / «останови секундомер»
    «выключи звук» / «включи звук», «прочитай буфер обмена»
"""

import ast
import operator
import random
import re
import socket
import time
from datetime import date

import core
from core import registry
from timeparse import words_to_digits, say_duration, _plural


# ---------- калькулятор ----------
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}

_CALC_WORDS = [
    (r"\bквадратный корень из\b|\bкорень квадратный из\b|\bкорень из\b", " sqrt "),
    (r"\bв квадрате\b", " ** 2 "), (r"\bв кубе\b", " ** 3 "),
    (r"\bв степени\b", " ** "),
    (r"\bумножить на\b|\bумножь на\b|\bпомножить на\b|\bумноженное на\b|\bх\b|\bx\b|×", " * "),
    (r"\bразделить на\b|\bподелить на\b|\bделить на\b|\bподели на\b|\bраздели на\b|÷", " / "),
    (r"\bплюс\b|\bприбавить\b", " + "),
    (r"\bминус\b|\bотнять\b|\bвычесть\b", " - "),
    (r"\bоткрой скобку\b", " ( "), (r"\bзакрой скобку\b", " ) "),
]
_CALC_PREFIX = re.compile(r"^(?:а\s+)?(?:сколько будет|сколько это|посчитай|вычисли|подсчитай|реши|калькулятор|сосчитай)\s*:?\s*")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:процент\w*|%)\s+от\s+(\d+(?:\.\d+)?)")


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("слишком большая степень")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "sqrt" and len(node.args) == 1:
        v = _eval(node.args[0])
        if v < 0:
            raise ValueError("корень из отрицательного")
        return v ** 0.5
    raise ValueError("не арифметика")


def _number(x):
    if isinstance(x, float) and x.is_integer() and abs(x) < 1e15:
        x = int(x)
    if isinstance(x, int):
        return f"{x:,}".replace(",", " ")
    return f"{x:.6g}".replace(".", ",") if abs(x) < 1e6 else f"{x:,.2f}".replace(",", " ").replace(".", ",")


def calculate(text):
    """Текст -> число или None (если это не арифметика)."""
    t = words_to_digits(text.lower().replace("ё", "е")).strip(" ?.!")
    t = _CALC_PREFIX.sub("", t)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    m = _PERCENT.search(t)
    if m:
        t = t[:m.start()] + f"({m.group(1)} / 100 * {m.group(2)})" + t[m.end():]
    for rx, op in _CALC_WORDS:
        t = re.sub(rx, op, t)
    t = re.sub(r"sqrt\s+(\d+(?:\.\d+)?|\([^()]*\))", r"sqrt(\1)", t).replace("^", "**")
    if not re.search(r"\d", t) or not re.fullmatch(r"[\d\s+\-*/().]*(?:sqrt[\d\s+\-*/().]*)*", t):
        return None
    if not re.search(r"[+\-*/]|sqrt", t):
        return None
    try:
        return _eval(ast.parse(t.strip(), mode="eval"))
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError, TypeError):
        return None


@registry.command(
    ["сколько будет", "посчитай", "вычисли", "подсчитай", "калькулятор", "сосчитай",
     "умножить на", "разделить на", "поделить на", "плюс", "минус", "корень из", "в квадрате",
     "процентов от"],
    "Калькулятор", "Утилиты", priority=6,
)
def calc(text):
    if "делить на ноль" in text or re.search(r"(?:раздели\w*|подели\w*|делить)\s+на\s+(?:0|ноль)\b", text):
        return "На ноль делить нельзя — даже мне."
    value = calculate(text)
    if value is None:
        return None          # «сколько будет 100 долларов в рублях» — это к курсам
    return f"Получается {_number(value)}."


# ---------- случайность ----------
@registry.command(
    ["подбрось монетку", "подкинь монетку", "брось монетку", "монетка", "орел или решка",
     "орёл или решка", "кинь монетку", "подбрось монету"],
    "Монетка", "Утилиты", priority=5,
)
def coin(text):
    return random.choice(["Орёл!", "Решка!"])


@registry.command(
    ["кинь кубик", "брось кубик", "подбрось кубик", "кубик", "кинь кости", "брось кости"],
    "Кубик", "Утилиты", priority=5,
)
def dice(text):
    n = 2 if re.search(r"\b(?:два|2|двa)\s+куб|кости", text) else 1
    rolls = [random.randint(1, 6) for _ in range(n)]
    return f"Выпало {rolls[0]}." if n == 1 else f"Выпало {rolls[0]} и {rolls[1]}, в сумме {sum(rolls)}."


@registry.command(
    ["случайное число", "рандомное число", "загадай число", "назови число", "выбери число"],
    "Случайное число", "Утилиты", priority=6,
)
def random_number(text):
    nums = [int(x) for x in re.findall(r"-?\d+", words_to_digits(text))]
    lo, hi = (min(nums[:2]), max(nums[:2])) if len(nums) >= 2 else (1, nums[0]) if nums else (1, 100)
    return f"{random.randint(lo, hi)}."


# ---------- повтори ----------
_last = {}         # source -> последний ответ (для «что ты сказала»)
_last_cmd = {}     # source -> (имя команды, фраза) — для «повтори»
_REPEAT_SKIP = {"repeat_last", "repeat_answer", "ai"}   # «повтори» и ответы GigaChat не повторяем


def _remember(source, name, text, response):
    if name in ("repeat_last", "repeat_answer"):
        return
    if response:
        _last[source] = response
    if name not in _REPEAT_SKIP:
        _last_cmd[source] = (name, text)


core.on_command(_remember)


@registry.command(
    ["повтори", "повтори команду", "повтори ещё раз", "повтори еще раз", "ещё раз", "еще раз",
     "сделай ещё раз", "сделай еще раз", "повтори это", "то же самое", "ещё разок"],
    "Повторить последнюю команду", "Общее", priority=4,
)
def repeat_last(text):
    """«Повтори» выполняет прошлую команду заново (новая песня, новый кубик, новое время),
    а не пересказывает её ответ. Опасные команды (выключение, клавиши) не повторяем."""
    prev = _last_cmd.get(core.current_source())
    if prev is None:
        return "Пока нечего повторять."
    name, phrase = prev
    cmd = next((c for c in registry.commands if c["name"] == name), None)
    if cmd is None or cmd.get("risky"):
        return "Эту команду повторять не буду — она опасная. Скажи её сам."
    return core.handle_command(phrase, source=core.current_source(), ai=False) or "Не вышло повторить."


@registry.command(
    ["что ты сказал", "что ты сказала", "не расслышал", "не расслышала", "скажи ещё раз ответ",
     "повтори ответ", "повтори что сказала", "что ты ответила"],
    "Повторить последний ответ", "Общее", priority=5,
)
def repeat_answer(text):
    return _last.get(core.current_source()) or "Пока нечего повторять."


# ---------- что ты умеешь ----------
_SKILLS = ("Я умею: включать музыку и ютуб, открывать и закрывать программы, говорить погоду и курсы валют, "
           "ставить таймеры, будильники и напоминания, записывать заметки, считать, управлять громкостью, "
           "мышкой и светом, делать скриншоты, переводить слова, играть в игры и рассказывать анекдоты. "
           "А на любой другой вопрос отвечу с помощью GigaChat.")


@registry.command(
    ["что ты умеешь", "что ты можешь", "твои возможности", "помощь", "список команд",
     "какие команды", "что умеешь", "что можешь", "help"],
    "Что умеет Кеша", "Общее", priority=6,
)
def skills(text):
    if "список команд" in text or "какие команды" in text:
        cats = {}
        for c in registry.commands:
            cats[c["category"]] = cats.get(c["category"], 0) + 1
        top = ", ".join(f"{k.lower()} — {v}" for k, v in sorted(cats.items(), key=lambda kv: -kv[1])[:8])
        return f"У меня {len(registry.commands)} команд. Больше всего: {top}."
    return _SKILLS


# ---------- анекдоты ----------
JOKES = [
    "Программист ставит на тумбочку два стакана: один с водой — если захочет пить, другой пустой — если не захочет.",
    "— Почему программисты путают Хэллоуин и Рождество? — Потому что 31 OCT равно 25 DEC.",
    "Учитель: «Вовочка, назови пять животных Африки». — «Три льва и два жирафа!»",
    "Компьютер обыграл меня в шахматы, но в боксе у него не было шансов.",
    "— Алло, это служба поддержки? У меня не работает клавиатура. — Нажмите любую клавишу. — А где клавиша «любая»?",
    "Оптимист учит китайский, пессимист — английский, реалист — автомат Калашникова. А я учу новые команды.",
    "Кот смотрит на холодильник так, будто знает пароль.",
    "Мама: «Иди спать!» Я: «Мне надо доделать уровень». Уровень: последний из ста.",
    "— Доктор, я всё время думаю, что я голосовой помощник. — И давно это у вас? — Скажите «Кеша», и узнаете.",
    "Ученик: «Можно выйти?» Учитель: «Можно». Ученик: «Ура, Wi-Fi в коридоре лучше!»",
    "Сапёр, который любит пиццу, всегда режет последний кусок очень осторожно.",
    "Почему у Майнкрафта нет проблем с деньгами? Потому что он всё время копит блоки.",
]


@registry.command(
    ["анекдот", "расскажи анекдот", "шутка", "пошути", "расскажи шутку", "рассмеши меня",
     "рассмеши", "смешное", "скажи шутку", "ещё анекдот", "еще анекдот"],
    "Анекдот", "Развлечения", priority=5,
)
def joke(text):
    return random.choice(JOKES)


# ---------- система ----------
@registry.command(
    ["нагрузка", "нагрузка компьютера", "загрузка процессора", "нагрузка процессора",
     "сколько памяти", "оперативная память", "оперативка", "состояние компьютера",
     "загрузка компьютера", "сколько места на диске", "место на диске"],
    "Нагрузка ПК", "Система", priority=5,
)
def system_load(text):
    import psutil
    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory()
    parts = [f"Процессор загружен на {cpu:.0f}%", f"память — {mem.percent:.0f}% "
             f"(свободно {mem.available / 2**30:.1f} ГБ)"]
    if "диск" in text or "мест" in text or "состояние" in text:
        try:
            d = psutil.disk_usage("C:\\")
            parts.append(f"на диске C свободно {d.free / 2**30:.0f} ГБ из {d.total / 2**30:.0f}")
        except Exception:
            pass
    hog = max(psutil.process_iter(["name", "memory_info"]),
              key=lambda p: (p.info.get("memory_info").rss if p.info.get("memory_info") else 0), default=None)
    if hog is not None and hog.info.get("name"):
        parts.append(f"больше всего памяти ест {hog.info['name'].removesuffix('.exe')}")
    return ", ".join(parts) + "."


def internet_ok(timeout=2.0):
    for host in ("1.1.1.1", "8.8.8.8", "77.88.8.8"):
        try:
            t = time.time()
            with socket.create_connection((host, 53), timeout=timeout):
                return (time.time() - t) * 1000
        except OSError:
            continue
    return None


@registry.command(
    ["есть ли интернет", "есть интернет", "проверь интернет", "работает ли интернет",
     "работает интернет", "пинг", "проверь связь", "интернет работает"],
    "Проверка интернета", "Система", priority=6,
)
def check_internet(text):
    ms = internet_ok()
    if ms is None:
        return "Интернета нет: ни один сервер не отвечает."
    return f"Интернет есть, отклик {ms:.0f} миллисекунд."


# ---------- звук ----------
def _endpoint():
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    dev = AudioUtilities.GetSpeakers()
    return cast(dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None), POINTER(IAudioEndpointVolume))


def set_mute(on):
    try:
        _endpoint().SetMute(1 if on else 0, None)
        return True
    except Exception as e:
        print(f"[mute] {e}")
        return False


@registry.command(
    ["выключи звук", "без звука", "отключи звук", "убери звук", "режим без звука", "замьють",
     "мьют", "mute"],
    "Выключить звук", "Громкость", priority=6,
)
def mute(text):
    return "Звук выключен." if set_mute(True) else "Не удалось выключить звук."


@registry.command(
    ["включи звук", "верни звук", "размьють", "unmute"],
    "Включить звук", "Громкость", priority=6,
)
def unmute(text):
    return "Звук включён." if set_mute(False) else "Не удалось включить звук."


# ---------- буфер обмена ----------
@registry.command(
    ["прочитай буфер", "прочитай буфер обмена", "что в буфере", "что в буфере обмена",
     "что я скопировал", "что я скопировала", "буфер обмена"],
    "Прочитать буфер обмена", "Система", priority=5,
)
def read_clipboard(text):
    try:
        import pyperclip
        clip = (pyperclip.paste() or "").strip()
    except Exception as e:
        print(f"[clipboard] {e}")
        return "Не удалось прочитать буфер обмена."
    if not clip:
        return "Буфер обмена пуст."
    return clip if len(clip) <= 300 else clip[:300] + "… и дальше ещё много текста."


# ---------- сколько дней до ----------
_MONTHS = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6, "июля": 7,
           "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
_ORD = {"первого": 1, "второго": 2, "третьего": 3, "четвертого": 4, "пятого": 5, "шестого": 6,
        "седьмого": 7, "восьмого": 8, "девятого": 9, "десятого": 10, "одиннадцатого": 11,
        "двенадцатого": 12, "тринадцатого": 13, "четырнадцатого": 14, "пятнадцатого": 15,
        "шестнадцатого": 16, "семнадцатого": 17, "восемнадцатого": 18, "девятнадцатого": 19,
        "двадцатого": 20, "тридцатого": 30}
_HOLIDAYS = [
    (r"нового года|новогодн", (1, 1), "Нового года"),
    (r"рождества", (1, 7), "Рождества"),
    (r"лета\b", (6, 1), "лета"), (r"осени\b", (9, 1), "осени"),
    (r"зимы\b", (12, 1), "зимы"), (r"весны\b", (3, 1), "весны"),
    (r"каникул", (6, 1), "летних каникул"),
    (r"8 марта|восьмого марта", (3, 8), "8 марта"),
    (r"23 февраля|двадцать третьего февраля", (2, 23), "23 февраля"),
    (r"дня знаний", (9, 1), "Дня знаний"),
    (r"хэллоуина|хеллоуина", (10, 31), "Хэллоуина"),
]


def _ordinals_to_digits(t):
    """«двадцать пятого» -> «25», «первого» -> «1»."""
    def tens(m):
        return str({"двадцать": 20, "тридцать": 30}[m.group(1)] + _ORD[m.group(2)])
    t = re.sub(r"\b(двадцать|тридцать)\s+(" + "|".join(_ORD) + r")\b", tens, t)
    return re.sub(r"\b(" + "|".join(_ORD) + r")\b", lambda m: str(_ORD[m.group(1)]), t)


def parse_day_month(text):
    """«5 мая», «двадцать пятого декабря» -> (месяц, день) или None."""
    t = words_to_digits(_ordinals_to_digits(text.lower().replace("ё", "е")))
    m = re.search(r"\b(\d{1,2})(?:-?го|-?е)?\s+(" + "|".join(_MONTHS) + r")\b", t)
    if not m:
        return None
    mo, d = _MONTHS[m.group(2)], int(m.group(1))
    try:
        date(2024, mo, d)          # високосный год: 29 февраля тоже допустимо
    except ValueError:
        return None
    return mo, d


def birthday():
    import settings
    v = settings.get("birthday")
    return tuple(v) if v else None


def days_until(text, today=None):
    """-> (дней, название) или None."""
    today = today or date.today()
    t = _ordinals_to_digits(text.lower().replace("ё", "е"))
    target = None
    if re.search(r"рожден|днюх", t) and birthday():
        mo, d = birthday()
        target = (mo, d, "твоего дня рождения")
    for rx, (mo, d), name in _HOLIDAYS:
        if target is None and re.search(rx, t):
            target = (mo, d, name)
            break
    if target is None:
        m = re.search(r"\b(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\b", t)
        if not m:
            return None
        target = (_MONTHS[m.group(2)], int(m.group(1)), f"{m.group(1)} {m.group(2)}")
    mo, d, name = target
    try:
        when = date(today.year, mo, d)
        if when < today:
            when = date(today.year + 1, mo, d)
    except ValueError:
        return None
    return (when - today).days, name


@registry.command(
    ["сколько дней до", "сколько осталось до", "сколько ждать до", "через сколько дней",
     "когда новый год", "скоро новый год"],
    "Сколько дней до даты", "Время", priority=6,
)
def days_left(text):
    res = days_until(text)
    if res is None:
        if re.search(r"рожден|днюх", text):
            return "Я не знаю, когда у тебя день рождения. Скажи, например: «мой день рождения 5 мая»."
        return None
    n, name = res
    if n == 0:
        if name == "твоего дня рождения":
            return "Так он же сегодня! С днём рождения! 🎉"
        return f"День {name} — сегодня!" if not name[0].isdigit() else f"{name} — это сегодня!"
    return f"До {name} {n} {_plural(n, 'день', 'дня', 'дней')}."


@registry.command(
    ["мой день рождения", "у меня день рождения", "запомни мой день рождения", "я родился",
     "я родилась", "когда мой день рождения", "когда у меня день рождения", "мой др",
     "запомни день рождения"],
    "Запомнить день рождения", "Время", priority=9,
)
def set_birthday(text):
    import settings
    md = parse_day_month(text)
    if md is None:
        if "когда" in text:
            b = birthday()
            return (f"Твой день рождения {b[1]} {list(_MONTHS)[b[0] - 1]}." if b else
                    "Не знаю. Скажи: «мой день рождения 5 мая».")
        if re.search(r"у меня (?:сегодня )?день рождения|сегодня мой день рождения", text):
            today = date.today()
            settings.set("birthday", [today.month, today.day])
            return "С днём рождения! 🎉 Запомнил, буду поздравлять."
        return "Скажи дату, например: «мой день рождения 5 мая»."
    settings.set("birthday", list(md))
    n, _ = days_until("до дня рождения")
    tail = "Это сегодня — с днём рождения! 🎉" if n == 0 else f"До него {n} {_plural(n, 'день', 'дня', 'дней')}."
    return f"Запомнил: {md[1]} {list(_MONTHS)[md[0] - 1]}. {tail}"


# ---------- сводка на день ----------
def _safe(fn, *args):
    try:
        return fn(*args) or ""
    except Exception as e:
        print(f"[briefing] {getattr(fn, '__name__', fn)}: {e}")
        return ""


@registry.command(
    ["сводка", "утренняя сводка", "брифинг", "сводка на день", "что на сегодня",
     "расскажи про сегодня", "план на день", "дай сводку"],
    "Сводка на день", "Время", priority=7,
)
def briefing(text):
    import commands
    from features import agenda, reminders
    parts = [_safe(commands.get_date, "какое сегодня число")]
    weather = _safe(commands.get_weather_cmd, "погода")
    if weather and not weather.startswith(("Ошибка", "Не нашёл")):
        parts.append(f"Погода: {weather.rstrip('.')}.")
    events = _safe(agenda.agenda_list, "что у меня сегодня")
    if events and "ничего" not in events:
        parts.append(f"В календаре: {events}")
    rem = _safe(reminders.list_reminders, "какие напоминания")
    if rem and not rem.startswith(("Напоминаний нет", "Будильников нет")):
        parts.append(f"Напоминания:\n{rem}")
    res = days_until("до дня рождения")
    if res and res[0] <= 7:
        parts.append("Сегодня твой день рождения! 🎉" if res[0] == 0 else
                     f"До дня рождения {res[0]} {_plural(res[0], 'день', 'дня', 'дней')}!")
    return "\n".join(p for p in parts if p)


# ---------- окна и папки ----------
@registry.command(
    ["покажи рабочий стол", "сверни все окна", "сверни всё", "сверни все", "убери все окна",
     "спрячь все окна", "сверни всё окна"],
    "Показать рабочий стол", "Окна", priority=8,
)
def show_desktop(text):
    import keyboard
    keyboard.send("win+d")
    return "Готово, рабочий стол."


def _home(*parts):
    from pathlib import Path
    return str(Path.home().joinpath(*parts))


FOLDERS = [
    (r"загрузк|скачанн", "Downloads", "Загрузки"),
    (r"документ", "Documents", "Документы"),
    (r"рабочий стол|рабочем столе", "Desktop", "Рабочий стол"),
    (r"картинк|изображени|фотограф\w* папк|папк\w* фото", "Pictures", "Изображения"),
    (r"папк\w* видео|видеозапис", "Videos", "Видео"),
    (r"папк\w* музык", "Music", "Музыка"),
]


@registry.command(
    ["открой загрузки", "открой папку загрузки", "открой документы", "открой мои документы",
     "открой папку документы", "открой рабочий стол", "открой папку рабочий стол",
     "открой картинки", "открой изображения", "открой папку изображения", "открой папку видео",
     "открой папку музыка", "покажи загрузки", "что я скачал",
     "открой корзину", "покажи корзину", "открой скачанные"],
    "Открыть папку", "Система", priority=6,
)
def open_folder(text):
    import os
    if "корзин" in text:
        os.startfile("shell:RecycleBinFolder")
        return "Открываю корзину."
    for rx, sub, name in FOLDERS:
        if re.search(rx, text):
            path = _home(sub)
            if not os.path.isdir(path):
                path = _home("OneDrive", sub)
            os.startfile(path)
            return f"Открываю папку «{name}»."
    return None          # «открой папку проекта …» — пусть разберётся open_app


@registry.command(
    ["очисти корзину", "очистить корзину", "опустоши корзину", "почисти корзину"],
    "Очистить корзину", "Система", priority=8, risky=True,
)
def empty_recycle_bin(text):
    import ctypes
    # 1|2|4: без подтверждения, без окна прогресса, без звука. 0 = успех, иначе пуста/ошибка
    rc = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
    return "Корзина очищена." if rc == 0 else "Корзина уже пуста."


# ---------- о себе ----------
@registry.command(
    ["ты кто", "кто ты", "как тебя зовут", "твое имя", "твоё имя", "представься",
     "расскажи о себе", "что ты такое", "кто тебя создал", "кто тебя сделал",
     "кто тебя написал", "кто твой создатель"],
    "Кто такой Кеша", "Основные", priority=9,
)
def about_me(text):
    if re.search(r"созд|сделал|написал", text):
        return "Меня написал мой хозяин на Python — по кусочку, волна за волной."
    return "Я Кеша — голосовой помощник этого компьютера. Скажи «что ты умеешь», и я расскажу."


@registry.command(
    ["ты тут", "ты здесь", "ты меня слышишь", "слышишь меня", "ты на связи", "ты слышишь",
     "алло", "ау", "ты жив", "ты живой", "проверка связи"],
    "Я здесь", "Основные", priority=9,
)
def are_you_here(text):
    return random.choice(["Да, я здесь!", "Тут, слушаю.", "На связи!", "Слышу тебя хорошо."])


@registry.command(
    ["что делаешь", "чем занимаешься", "чем занят", "что ты делаешь"],
    "Что делаешь", "Основные", priority=9,
)
def what_doing(text):
    return random.choice(["Слушаю тебя и жду команды.", "Слежу за компьютером. Что нужно?",
                          "Отдыхаю, пока ты не позовёшь."])


# ---------- секундомер ----------
_sw = {"start": None, "acc": 0.0}


def _elapsed():
    return _sw["acc"] + (time.time() - _sw["start"] if _sw["start"] else 0.0)


def _say_elapsed(sec):
    if sec < 60:
        return f"{sec:.1f}".replace(".", ",") + " секунды"     # дробное: «12,3 секунды»
    return say_duration(int(sec))


@registry.command(
    ["секундомер", "запусти секундомер", "включи секундомер", "старт секундомер",
     "останови секундомер", "стоп секундомер", "выключи секундомер", "сколько на секундомере",
     "сбрось секундомер", "сколько прошло"],
    "Секундомер", "Время", priority=7,
)
def stopwatch(text):
    if re.search(r"сбрось|обнули", text):
        _sw.update(start=None, acc=0.0)
        return "Секундомер сброшен."
    if re.search(r"останов|стоп|выключи|хватит", text):
        if _sw["start"] is None and not _sw["acc"]:
            return "Секундомер и не был запущен."
        sec = _elapsed()
        _sw.update(start=None, acc=0.0)
        return f"Стоп! Прошло {_say_elapsed(sec)}."
    if re.search(r"сколько", text):
        if _sw["start"] is None and not _sw["acc"]:
            if "секундомер" not in text:
                return None      # «сколько прошло дней с …» — не ко мне
            return "Секундомер не запущен. Скажи «запусти секундомер»."
        return f"Прошло {_say_elapsed(_elapsed())}."
    if _sw["start"] is not None:
        return f"Секундомер уже идёт: {_say_elapsed(_elapsed())}."
    _sw.update(start=time.time(), acc=0.0)
    return "Секундомер пошёл! Скажи «стоп секундомер», когда закончишь."


# ---------- Wi-Fi ----------
@registry.command(
    ["wi-fi", "wifi", "wi fi", "вайфай", "вай фай", "вай-фай", "открой вайфай", "настройки вайфай",
     "подключись к вайфаю", "список сетей"],
    "Настройки Wi-Fi", "Система", priority=6,
)
def open_wifi(text):
    import os
    os.startfile("ms-settings:network-wifi")
    return "Открываю настройки Wi-Fi."
