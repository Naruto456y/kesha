"""
Все команды проекта Кеша.
Каждая команда регистрируется через @registry.command.

Шаблон:
    @registry.command(patterns, description, category, priority)
    def my_command(text):
        # ... логика ...
        return "Что сказать пользователю"
"""

from core import registry

import os
import re
import sys
import time
import random
import webbrowser
import subprocess
import threading
from urllib.parse import quote
from datetime import datetime, timedelta, date
from pathlib import Path

import keyboard
import mouse
import psutil
import requests
import AppOpener


from config import (
    APP_PATHS, GAMES_PATHS, TIMER_PATH,
    WEATHER_API_KEY, WEATHER_CITY,
    GREETINGS, THANKS_RESPONSES, OK_RESPONSES, SEARCH_RESPONSES,
)

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from help_manager import GigaChat, Manager
    Manager.load_env()
    _gig = GigaChat()
    GIGACHAT_AVAILABLE = True
except Exception as e:
    print(f"[commands] GigaChat недоступен: {e}")
    _gig = None
    GIGACHAT_AVAILABLE = False

BASE_DIR = Path(__file__).parent


def _r(lst):
    return random.choice(lst)


def _launch_game(key):
    path = GAMES_PATHS.get(key)
    if path and os.path.exists(path):
        try:
            subprocess.Popen([sys.executable, path], shell=False)
            return "Запускаю игру"
        except Exception as e:
            return f"Ошибка запуска: {e}"
    return "Файл игры не найден"


def _get_volume():
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(interface, POINTER(IAudioEndpointVolume))
        return vol.GetMasterVolumeLevelScalar()
    except Exception:
        return 0.5


def _set_volume(level):
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(interface, POINTER(IAudioEndpointVolume))
        vol.SetMasterVolumeLevelScalar(max(0.0, min(1.0, level)), None)
        return True
    except Exception:
        return False


def _extract_query(text, words):
    q = text.lower()
    for w in sorted(words, key=len, reverse=True):   # сначала длинные фразы
        q = q.replace(w, "")
    return " ".join(q.split())


def _mouse_patterns(*directions):
    return [f"{noun} {d}" for noun in ("мышь", "мышку", "курсор", "указатель")
            for d in directions]


def _scroll_patterns(direction):
    verbs = ("скролл", "скролль", "прокрути", "пролистай", "листай", "промотай")
    return [f"{v} {direction}" for v in verbs]


_TYPE_WORDS = ["напечатай текст", "набери текст", "введи текст",
               "напечатай", "набери", "введи", "напиши"]
_KEY_WORDS = ["нажми на клавишу", "нажми клавишу", "нажми на кнопку", "нажми кнопку", "нажми"]
_YT_WORDS = ["найди в ютуби", "найди в ютубе", "найди на ютубе", "найди в ютюбе",
             "найди в youtube", "найди на youtube", "поищи в ютубе", "поищи на ютубе",
             "поищи в youtube", "ищи в ютубе", "видео в ютубе", "найди видео",
             "поищи видео", "покажи видео", "найди ролик"]
_WEB_WORDS = ["найди в интернете", "поищи в интернете", "найди в яндексе",
              "поищи в яндексе", "найди в гугле", "поищи в гугле",
              "найди информацию о", "найди информацию об", "найди информацию про",
              "поищи информацию о", "найди", "поищи", "погугли", "загугли",
              "поиск", "пробей"]
_MUSIC_WORDS = ["включи музыку", "поставь музыку", "запусти музыку", "давай музыку",
                "сыграй музыку", "включи песню", "поставь песню", "сыграй песню",
                "включи трек", "поставь трек", "включи музон", "поставь музон",
                "послушаем музыку",
                "музыка", "музон", "музло", "трек", "песня"]
_OPEN_WORDS = ["открой приложение", "открой программу", "запусти приложение",
               "запусти программу", "открой", "запусти"]
_CLOSE_WORDS = ["закрой приложение", "закрой программу", "закрыть программу",
                "завершить программу", "закрой", "закрыть"]
_DRAW_WORDS = ["нарисуй", "покажи картинку", "покажи картинки", "покажи изображение",
               "покажи фото", "найди картинку", "найди картинки", "найди изображение",
               "найди фото", "как выглядит", "изображение", "картинку", "картинки"]
_TR_EN = ["переведи на английский язык", "переведи на английский", "переведи на английском",
          "переведи по английски", "переведи по-английски", "переведи на инглиш",
          "переведи на англ", "как будет по английски", "как будет по-английски",
          "как сказать по английски", "как сказать по-английски",
          "как по английски", "как по-английски", "перевод на английский"]
_TR_RU = ["переведи на русский язык", "переведи на русский", "переведи на русском",
          "переведи по русски", "переведи по-русски", "переведи на рус",
          "как будет по русски", "как будет по-русски", "как сказать по русски",
          "как сказать по-русски", "как по русски", "как по-русски", "перевод на русский"]
_TIMER_WORDS = ["поставь таймер на", "поставь таймер", "заведи таймер на", "заведи таймер",
                "включи таймер на", "включи таймер", "запусти таймер на", "запусти таймер",
                "засеки время", "засеки", "таймер на", "таймер"]
_LIGHT_ON = ["включи лампу", "включи свет", "включи светильник", "включи лампочку",
             "включи освещение", "включи верхний свет", "зажги свет", "зажги лампу",
             "зажги лампочку", "зажги светильник", "дай свет"]
_LIGHT_OFF = ["выключи лампу", "выключи свет", "выключи светильник", "выключи лампочку",
              "выключи освещение", "погаси свет", "погаси лампу", "погаси лампочку",
              "погаси светильник", "убери свет", "выруби свет", "потуши свет", "отключи свет"]
_BRIGHT = ["поставь яркость", "установи яркость", "сделай яркость", "выставь яркость",
           "измени яркость", "яркость на", "яркость"]
_TEMP = ["поставь цветовую температуру", "установи цветовую температуру",
         "выставь цветовую температуру", "поставь температуру света",
         "выставь температуру света", "цветовая температура", "цветовую температуру",
         "температура света", "температуру света"]
_STATUS = ["статус лампы", "статус света", "статус светильника", "состояние лампы",
           "состояние света", "горит ли свет", "горит ли лампа", "включен ли свет",
           "включён ли свет", "включена ли лампа", "свет горит", "лампа горит"]


# ============================================================
#  ОСНОВНЫЕ
# ============================================================

@registry.command(
    ["привет", "здравствуй", "здравствуйте", "хай", "добрый день", "добрый вечер",
     "доброе утро", "доброй ночи", "приветствую", "приветик", "здарова", "здорово",
     "салют", "йоу", "хеллоу", "hello"],
    "Поздороваться", "Основные", priority=10,
)
def greeting(text):
    return _r(GREETINGS)


@registry.command(
    ["как дела", "как жизнь", "как настроение", "как ты", "как поживаешь",
     "как твои дела", "как у тебя дела", "как сам", "как оно", "как самочувствие"],
    "Узнать состояние", "Основные", priority=10,
)
def how_are_you(text):
    return "Всё отлично! Готов к работе."


@registry.command(
    ["молодец", "спасибо", "благодарю", "умница", "красава", "мерси", "благодарствую",
     "респект", "умничка", "хорошая работа", "отличная работа", "ты лучший",
     "ты лучшая", "браво", "так держать"],
    "Похвалить", "Основные", priority=10,
)
def thanks(text):
    return _r(THANKS_RESPONSES)


@registry.command(
    ["пока", "выход", "выключись", "до свидания", "прощай", "до встречи", "до скорого",
     "увидимся", "всего доброго", "всего хорошего", "хорошего дня", "бывай",
     "спокойной ночи", "покеда", "чао", "bye"],
    "Попрощаться", "Основные", priority=20,
)
def goodbye(text):
    return "До свидания!"


# ============================================================
#  СИСТЕМНАЯ ИНФОРМАЦИЯ
# ============================================================

@registry.command(
    ["время", "который час", "сколько времени", "сколько сейчас времени",
     "который сейчас час", "сколько на часах", "сколько там времени"],
    "Текущее время", "Система",
)
def get_time(text):
    return f"Сейчас {datetime.now().strftime('%H:%M')}"


@registry.command(
    ["дата", "какое сегодня число", "какой сегодня день", "какое число",
     "какая сегодня дата", "какое число сегодня", "сегодняшняя дата",
     "какой сегодня день недели", "какой день недели"],
    "Текущая дата", "Система",
)
def get_date(text):
    return f"Сегодня {datetime.now().strftime('%d.%m.%Y')}"


@registry.command(
    ["батарея", "заряд", "уровень заряда", "состояние батареи", "батарейка",
     "сколько заряда", "сколько процентов", "сколько осталось заряда",
     "что с батареей", "сколько батареи", "сколько зарядки", "процент заряда"],
    "Уровень батареи", "Система",
)
def get_battery(text):
    b = psutil.sensors_battery()
    if not b:
        return "Информация о батарее недоступна"
    status = "заряжается" if b.power_plugged else "от батареи"
    return f"Батарея {status}. Уровень: {b.percent}%"


# ============================================================
#  ПИТАНИЕ
# ============================================================

@registry.command(
    ["выключи компьютер", "выключи комп", "выключи пк", "выключи ноутбук",
     "выруби компьютер", "выруби комп", "выруби пк", "отключи компьютер",
     "заверши работу", "шатдаун", "shutdown"],
    "Выключить ПК", "Система", risky=True,
)
def shutdown_pc(text):
    os.system("shutdown /s /t 10")
    return "Выключаю компьютер через 10 секунд"


@registry.command(
    ["перезагрузка", "перезагрузи компьютер", "перезагрузи комп", "перезагрузи пк",
     "перезагрузи ноутбук", "перезапусти компьютер", "перезапусти комп",
     "ребут", "рестарт", "рестартни комп"],
    "Перезагрузить ПК", "Система", risky=True,
)
def restart_pc(text):
    os.system("shutdown /r /t 5")
    return "Перезагружаю компьютер"


@registry.command(
    ["спящий режим", "уснуть", "спать", "сон", "в спящий режим", "режим сна",
     "усыпи компьютер", "усыпи комп", "засыпай"],
    "Спящий режим", "Система", risky=True,
)
def sleep_pc(text):
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "Ухожу в спящий режим"


@registry.command(
    ["заблокируй компьютер", "блокировка", "заблокируй пк", "блокни", "заблокируй",
     "заблокируй комп", "заблокируй экран", "заблокировать компьютер",
     "залочь комп", "лочь комп"],
    "Заблокировать ПК", "Система",
)
def lock_pc(text):
    os.system("rundll32.exe user32.dll,LockWorkStation")
    return "Экран заблокирован"


@registry.command(
    ["отмени выключение", "отмени перезагрузку", "отмена выключения", "отбой выключения",
     "не выключай компьютер", "не выключай комп", "отмени shutdown",
     "отмени завершение работы"],
    "Отменить выключение/перезагрузку", "Система", priority=25,
)
def cancel_shutdown(text):
    r = subprocess.run(["shutdown", "/a"], capture_output=True)
    if r.returncode == 0:
        return "Отменил, компьютер не выключится"
    return "Нечего отменять"


# ============================================================
#  ОКНА
# ============================================================

@registry.command(
    ["сверни окно", "сверни", "свернуть окно", "свернуть", "сверни это окно",
     "спрячь окно", "убери окно", "минимизируй окно", "минимизируй", "сверни программу"],
    "Свернуть окно", "Система",
)
def minimize_window(text):
    keyboard.send("win+down")
    return _r(OK_RESPONSES)


@registry.command(
    ["закрой окно", "закрой это окно", "закрыть окно", "закрой текущее окно",
     "закрой активное окно", "закрой это"],
    "Закрыть окно", "Система", priority=5, risky=True,
)
def close_window(text):
    keyboard.send("alt+f4")
    return _r(OK_RESPONSES)


@registry.command(
    ["открой проводник", "проводник", "файловый менеджер", "папка", "запусти проводник",
     "открой папку", "открой файлы", "покажи файлы", "открой мой компьютер",
     "открой этот компьютер"],
    "Открыть проводник", "Система", priority=5,
)
def open_explorer(text):
    keyboard.send("win+e")
    return "Проводник открыт"


@registry.command(
    ["открой настройки", "настройки", "параметры", "открой параметры",
     "зайди в настройки", "покажи настройки", "настройки windows", "настройки винды"],
    "Открыть настройки", "Система", priority=5,
)
def open_settings(text):
    keyboard.send("win+i")
    return "Настройки открыты"


# ============================================================
#  ГРОМКОСТЬ
# ============================================================

@registry.command(
    ["громче", "увеличь громкость", "прибавь громкость", "погромче", "добавь громкость",
     "добавь звук", "прибавь звук", "повысь громкость", "звук погромче",
     "слишком тихо", "не слышно", "ничего не слышно"],
    "Громкость +", "Медиа", priority=5,
)
def volume_up(text):
    new = min(1.0, _get_volume() + 0.1)
    _set_volume(new)
    return f"Громкость {int(new * 100)}%"


@registry.command(
    ["тише", "уменьши громкость", "сбавь громкость", "потише", "убавь громкость",
     "убавь звук", "понизь громкость", "уменьши звук", "слишком громко",
     "очень громко", "не так громко"],
    "Громкость −", "Медиа", priority=5,
)
def volume_down(text):
    new = max(0.0, _get_volume() - 0.1)
    _set_volume(new)
    return f"Громкость {int(new * 100)}%"


@registry.command(
    ["громкость", "поставь громкость", "установи громкость", "выставь громкость",
     "сделай громкость", "измени громкость", "звук на", "поставь звук на",
     "максимальная громкость", "минимальная громкость", "на полную громкость"],
    "Установить громкость", "Медиа",
)
def set_volume(text):
    if "макс" in text:
        _set_volume(1.0)
        return "Максимальная громкость"
    if "мин" in text:
        _set_volume(0.0)
        return "Минимальная громкость"
    digits = "".join(filter(str.isdigit, text))
    if digits:
        vol = max(0, min(100, int(digits)))
        _set_volume(vol / 100)
        return f"Громкость {vol}%"
    return "Не понял громкость"


# ============================================================
#  МЫШЬ
# ============================================================

def _mouse_step(text, default=50):
    """«мышь вправо 25» -> 25 пикселей (1..500), без числа — default."""
    import re
    m = re.search(r"\d+", text)
    return max(1, min(500, int(m.group()))) if m else default


@registry.command(
    _mouse_patterns("вверх", "выше", "наверх"),
    "Мышь вверх", "Система", priority=5,
)
def mouse_up(text):
    mouse.move(0, -_mouse_step(text), absolute=False, duration=0.1)
    return "Мышь вверх"


@registry.command(
    _mouse_patterns("вниз", "ниже"),
    "Мышь вниз", "Система", priority=5,
)
def mouse_down(text):
    mouse.move(0, _mouse_step(text), absolute=False, duration=0.1)
    return "Мышь вниз"


@registry.command(
    _mouse_patterns("влево", "левее"),
    "Мышь влево", "Система", priority=5,
)
def mouse_left(text):
    mouse.move(-_mouse_step(text), 0, absolute=False, duration=0.1)
    return "Мышь влево"


@registry.command(
    _mouse_patterns("вправо", "правее"),
    "Мышь вправо", "Система", priority=5,
)
def mouse_right(text):
    mouse.move(_mouse_step(text), 0, absolute=False, duration=0.1)
    return "Мышь вправо"


@registry.command(
    ["левый клик", "левый", "лкм", "кликни", "клик", "щелкни", "щёлкни",
     "нажми лкм", "кликни левой", "левая кнопка мыши"],
    "ЛКМ", "Система",
)
def click_left(text):
    mouse.click("left")
    return "Левый клик"


@registry.command(
    ["правый клик", "правый", "пкм", "кликни правой", "щелкни правой", "щёлкни правой",
     "нажми пкм", "правая кнопка мыши", "контекстное меню"],
    "ПКМ", "Система", priority=2,
)
def click_right(text):
    mouse.click("right")
    return "Правый клик"


@registry.command(
    _scroll_patterns("вниз") + ["прокрути страницу вниз", "пролистай страницу вниз",
                                "прокрути ниже", "опусти страницу"],
    "Скролл вниз", "Система", priority=5,
)
def scroll_down(text):
    mouse.wheel(-3)
    return "Скролл вниз"


@registry.command(
    _scroll_patterns("вверх") + ["прокрути страницу вверх", "пролистай страницу вверх",
                                 "прокрути выше", "подними страницу"],
    "Скролл вверх", "Система", priority=5,
)
def scroll_up(text):
    mouse.wheel(3)
    return "Скролл вверх"


# ============================================================
#  КЛАВИАТУРА
# ============================================================

@registry.command(
    _TYPE_WORDS,
    "Напечатать текст", "Система", risky=True,
)
def type_text(text):
    t = _extract_query(text, _TYPE_WORDS)
    if t:
        keyboard.write(t)
        return f"Напечатал: {t}"
    return "Что напечатать?"


@registry.command(
    _KEY_WORDS,
    "Нажать клавишу", "Система", risky=True,
)
def press_key(text):
    key = _extract_query(text, _KEY_WORDS)
    if key:
        try:
            keyboard.send(key)
            return f"Нажал {key}"
        except Exception as e:
            return f"Не удалось нажать {key}: {e}"
    return "Какую клавишу?"


# ============================================================
#  ПОИСК И ИНТЕРНЕТ
# ============================================================

@registry.command(
    _YT_WORDS,
    "Поиск на YouTube", "Интернет", priority=5, followup="найди в ютубе {arg}",
)
def search_youtube(text):
    query = _extract_query(text, _YT_WORDS)
    if not query:
        return "Что искать?"
    try:
        from youtube_search import YoutubeSearch
        results = YoutubeSearch(query, max_results=1).to_dict()
        if results:
            webbrowser.open(f"https://youtube.com{results[0]['url_suffix']}")
            return "Вот что удалось найти"
    except Exception as e:
        print(f"[youtube] {e}")
    return "Не удалось найти видео"


@registry.command(
    _WEB_WORDS,
    "Поиск в интернете", "Интернет", followup="найди {arg}",
)
def search_web(text):
    query = _extract_query(text, _WEB_WORDS)
    if not query:
        return "Что искать?"
    webbrowser.open(f"https://yandex.ru/search/?text={quote(query)}")
    return _r(SEARCH_RESPONSES)


@registry.command(
    ["youtube", "ютуб", "открой ютуб", "ютюб", "ютьюб", "запусти ютуб",
     "зайди на ютуб", "включи ютуб", "покажи ютуб"],
    "Открыть YouTube", "Интернет", priority=5,
)
def open_youtube(text):
    webbrowser.open("https://youtube.com")
    return _r(OK_RESPONSES)


# ---- погода: город из фразы ----

_CITY_RE = re.compile(r"\b(?:в|во)\s+([a-zа-яё\-]+(?:\s+[a-zа-яё\-]+)?)")
_CITY_STOP = {"сегодня", "завтра", "сейчас", "послезавтра", "вечером", "утром",
              "днем", "днём", "ночью", "на", "по", "и", "а"}
_CITY_ALIASES = {
    "питер": "Санкт-Петербург", "питере": "Санкт-Петербург", "спб": "Санкт-Петербург",
    "петербург": "Санкт-Петербург", "петербурге": "Санкт-Петербург",
    "санкт-петербурге": "Санкт-Петербург", "санкт петербурге": "Санкт-Петербург",
    "мск": "Москва", "екб": "Екатеринбург", "нск": "Новосибирск",
    "нижнем новгороде": "Нижний Новгород", "ростове": "Ростов-на-Дону",
    "ростове-на-дону": "Ростов-на-Дону", "нью-йорке": "Нью-Йорк",
    "нью йорке": "Нью-Йорк", "сочи": "Сочи",
}


def _extract_city(text):
    """«погода в Питере сегодня» -> «питере»; без города — город по умолчанию."""
    m = _CITY_RE.search(text.lower())
    if not m:
        return WEATHER_CITY
    words = []
    for w in m.group(1).split():
        if w in _CITY_STOP:
            break
        words.append(w)
    return " ".join(words) or WEATHER_CITY


def _city_candidates(name):
    """Предложный падеж -> варианты названия: «москве» -> москва, «казани» -> казань."""
    key = name.lower()
    if key in _CITY_ALIASES:
        return [_CITY_ALIASES[key]]
    words = key.split()
    head, last = " ".join(words[:-1]), words[-1]
    stems = [last, last[:-1] + "а", last[:-1] + "я", last[:-1] + "ь", last[:-1], last[:-2] + "ий"]
    out = []
    for s in stems:
        cand = f"{head} {s}".strip()
        if cand not in out and len(s) > 1:
            out.append(cand)
    return out


def _fetch_weather(city):
    """-> dict ответа OpenWeather или None, если такого города нет."""
    r = requests.get(
        "http://api.openweathermap.org/data/2.5/weather",
        params={"q": city, "appid": WEATHER_API_KEY, "units": "metric", "lang": "ru"},
        timeout=10,
    )
    if r.status_code == 404:
        return None
    return r.json()


@registry.command(
    ["погода", "температура на улице", "какая погода", "что на улице", "погоду", "погоде",
     "погодка", "прогноз", "сколько градусов", "какая температура", "что с погодой",
     "как на улице", "холодно ли", "тепло ли"],
    "Узнать погоду", "Интернет", followup="погода в {arg}",
)
def get_weather_cmd(text):
    name = _extract_city(text)
    try:
        for candidate in _city_candidates(name):
            data = _fetch_weather(candidate)
            if data:
                temp = round(data["main"]["temp"])
                desc = data["weather"][0]["description"]
                return f"{data.get('name', candidate)}: {temp}°C, {desc}"
        return f"Не нашёл город {name}"
    except Exception as e:
        return f"Ошибка погоды: {e}"


@registry.command(
    ["переводчик", "открой переводчик", "запусти переводчик", "яндекс переводчик",
     "гугл переводчик", "включи переводчик", "нужен переводчик"],
    "Открыть переводчик", "Интернет", priority=5,
)
def open_translator(text):
    webbrowser.open("https://translate.yandex.ru/")
    return _r(OK_RESPONSES)


@registry.command(
    ["дипси", "deepseek", "чат gpt", "дипсик", "дипсек", "deep seek", "чат гпт",
     "чатгпт", "chatgpt", "нейросеть", "открой нейросеть"],
    "Открыть DeepSeek", "Интернет", priority=5,
)
def open_deepseek(text):
    webbrowser.open("https://chat.deepseek.com/")
    return "Открываю DeepSeek"


@registry.command(
    ["игры яндекс", "яндекс игры", "поиграть", "хочу играть", "давай поиграем",
     "поиграем", "игры онлайн", "браузерные игры", "открой яндекс игры"],
    "Открыть Яндекс Игры", "Интернет", priority=5,
)
def open_yandex_games(text):
    webbrowser.open("https://yandex.ru/games/")
    return "Открываю Яндекс Игры"


# ============================================================
#  УЧЁБА
# ============================================================

@registry.command(
    ["дз", "домашнее задание", "домашка", "домашку", "домашнее", "что задали",
     "что задано", "что по дз", "открой дз", "покажи дз", "дз на завтра",
     "что на дом", "задания на дом"],
    "ДЗ", "Учёба",
)
def school_homework(text):
    webbrowser.open("https://school.mos.ru/diary/homeworks/")
    return "Открываю домашнее задание"


@registry.command(
    ["оценки", "отметки", "мои оценки", "оценка", "какие у меня оценки", "какие оценки",
     "покажи оценки", "открой оценки", "мои отметки", "что в журнале",
     "электронный журнал"],
    "Оценки", "Учёба",
)
def school_marks(text):
    webbrowser.open("https://school.mos.ru/diary/marks/current-marks")
    return "Показываю оценки"


@registry.command(
    ["расписание", "расписание на завтра", "уроки на завтра", "какие завтра уроки",
     "какие уроки", "что завтра по расписанию", "что завтра по урокам",
     "что завтра в школе", "покажи расписание", "открой расписание"],
    "Расписание на завтра", "Учёба",
)
def school_schedule(text):
    tomorrow = date.today() + timedelta(days=1)
    webbrowser.open(
        f"https://school.mos.ru/diary/schedules/day/"
        f"?date={tomorrow.strftime('%d-%m-%Y')}"
    )
    return "Расписание на завтра"


# ============================================================
#  ПРИЛОЖЕНИЯ
# ============================================================

@registry.command(
    ["открой minecraft", "открой майнкрафт", "майн", "майнкрафт", "minecraft",
     "маенкрафт", "майнкрафта", "хочу в майнкрафт"],
    "Запустить Minecraft", "Игры", priority=5,
)
def open_minecraft(text):
    path = APP_PATHS.get("майнкрафт")
    if path and os.path.exists(path):
        os.startfile(path)
        return "Открываю Minecraft"
    return "Не нашёл Minecraft"


@registry.command(
    ["открой roblox", "роблокс", "открой роблокс", "roblox", "роблакс",
     "хочу в роблокс"],
    "Запустить Roblox", "Игры", priority=5,
)
def open_roblox(text):
    path = APP_PATHS.get("роблокс")
    if path and os.path.exists(path):
        os.startfile(path)
        return "Открываю Roblox"
    return "Не нашёл Roblox"


@registry.command(
    ["браузер", "открой браузер", "интернет", "яндекс", "запусти браузер",
     "включи браузер", "открой интернет", "зайди в интернет", "выйти в интернет",
     "хочу в интернет", "яндекс браузер"],
    "Открыть браузер", "Система", priority=5,
)
def open_browser(text):
    path = APP_PATHS.get("яндекс") or APP_PATHS.get("браузер")
    if path and os.path.exists(path):
        os.startfile(path)
    else:
        webbrowser.open("https://yandex.ru")
    return "Браузер открыт"


@registry.command(
    ["открой вс код", "открой visual studio code", "открой vs code", "открой визуалку",
     "запусти вс код", "запусти vs code", "запусти visual studio code",
     "запусти визуалку", "вс код", "vs code", "визуалка", "открой вскод",
     "открой редактор кода", "открой среду разработки"],
    "Открыть VS Code", "Система", priority=6,
)
def open_vscode(text):
    path = APP_PATHS.get("visual studio code") or APP_PATHS.get("вс код")
    if path and os.path.exists(path):
        os.startfile(path)
        return "Открываю Visual Studio Code"
    keyboard.send("win+1")
    return "Открываю Visual Studio Code"


@registry.command(
    _OPEN_WORDS,
    "Открыть приложение", "Система",
)
def open_app(text):
    skip = [
        "проводник", "настройки", "roblox", "роблокс",
        "minecraft", "майн", "камер", "селфи", "браузер", "яндекс",
        "ютуб", "youtube", "дипси", "deepseek", "переводчик",
        "игры", "музык", "вол", "избр", "вс код", "visual studio", "vs code",
    ]
    if any(s in text for s in skip):
        return None

    app = _extract_query(text, _OPEN_WORDS)
    if not app:
        return "Что открыть?"

    for key, path in APP_PATHS.items():
        if key in app:
            if os.path.exists(path):
                try:
                    os.startfile(path)
                    return f"Открываю {app}"
                except Exception:
                    pass

    try:
        AppOpener.open(app, match_closest=True)
        return f"Открываю {app}"
    except Exception:
        return f"Не нашёл {app}"


@registry.command(
    _CLOSE_WORDS,
    "Закрыть приложение", "Система", risky=True,
)
def close_app(text):
    app = _extract_query(text, _CLOSE_WORDS)
    if not app:
        return "Что закрыть?"
    try:
        AppOpener.close(app, match_closest=True)
        return f"Закрываю {app}"
    except Exception:
        return f"Не удалось закрыть {app}"


# ============================================================
#  ИГРЫ
# ============================================================

@registry.command(
    ["камень ножницы бумага", "камень ножницы бумагу", "камень ножницы", "кнб"],
    "Игра: КНБ", "Игры", priority=5,
)
def game_rps(text):
    return _launch_game("камень ножницы бумага")


@registry.command(["виселица", "виселицу", "виселице"], "Игра: Виселица", "Игры", priority=5)
def game_hangman(text):
    return _launch_game("виселица")


@registry.command(["викторина", "викторину", "квиз", "quiz"], "Игра: Викторина", "Игры", priority=5)
def game_quiz(text):
    return _launch_game("викторина")


@registry.command(["квест", "квеста", "квесты"], "Игра: Квест", "Игры", priority=5)
def game_quest(text):
    return _launch_game("квест")


@registry.command(
    ["крестики-нолики", "крестики нолики", "крестики-нулики", "крестики нулики",
     "крестики"],
    "Игра: Крестики-нолики", "Игры", priority=5,
)
def game_tictactoe(text):
    return _launch_game("крестики-нолики")


@registry.command(
    ["угадай число", "угадай цифру", "угадать число", "отгадай число", "угадайку"],
    "Игра: Угадай число", "Игры", priority=5,
)
def game_guess(text):
    return _launch_game("угадай число")


# ============================================================
#  МЕДИА
# ============================================================

@registry.command(
    _MUSIC_WORDS,
    "Включить музыку", "Медиа",
)
def play_music(text):
    query = _extract_query(text, _MUSIC_WORDS)
    if query:
        try:
            AppOpener.open("Yandex", True)
            webbrowser.open(f"https://music.yandex.ru/search?text={quote(query)}")
            return f"Ищу: {query}"
        except Exception:
            return "Ошибка запуска музыки"
    webbrowser.open("https://music.yandex.ru/")
    return "Открываю Яндекс.Музыку"


@registry.command(
    ["моя волна", "волну", "избранное", "мою волну", "любимое", "включи мою волну",
     "включи волну", "поставь мою волну", "поставь волну", "мою музыку"],
    "Моя волна", "Медиа",
)
def play_wave(text):
    try:
        AppOpener.open("Yandex", True)
        webbrowser.open("https://music.yandex.ru/")
        time.sleep(2)
        keyboard.send("k")
        return "Включаю мою волну"
    except Exception:
        return "Ошибка"


@registry.command(
    ["пауза", "стоп музыка", "заткнись", "выключи музыку", "стоп", "останови музыку",
     "останови", "поставь на паузу", "на паузу", "хватит музыки", "выруби музыку",
     "отключи музыку", "замолчи", "помолчи", "останови песню", "останови трек"],
    "Пауза", "Медиа", priority=5,
)
def music_pause(text):
    keyboard.send("k")
    return "Пауза"


@registry.command(
    ["продолжи музыку", "продолжай музыку", "сними с паузы", "возобнови музыку",
     "возобнови", "продолжи воспроизведение", "продолжи играть"],
    "Продолжить после паузы", "Медиа", priority=5,
)
def music_resume(text):
    keyboard.send("k")
    return "Продолжаю"


@registry.command(
    ["дальше", "следующий трек", "некст", "следующая песня", "следующий", "следующая",
     "следующую", "next", "переключи трек", "переключи песню", "пропусти трек",
     "пропусти песню", "скипни", "скип", "другую песню", "другой трек"],
    "Следующий трек", "Медиа", priority=5,
)
def music_next(text):
    keyboard.send("n")
    return "Следующий"


@registry.command(
    ["предыдущий", "прошлый трек", "предыдущая песня", "предыдущую", "предыдущий трек",
     "прошлую песню", "прошлая песня", "верни трек", "верни песню", "верни прошлую",
     "трек назад", "песню назад", "включи предыдущий", "включи прошлую"],
    "Предыдущий трек", "Медиа", priority=5,
)
def music_prev(text):
    keyboard.send("p")
    return "Предыдущий"


@registry.command(
    ["лайк", "нравится", "мне нравится", "поставь лайк", "добавь в избранное",
     "добавь в любимое", "лайкни", "лайкни песню", "хорошая песня", "отличная песня",
     "крутая песня", "люблю эту песню", "сохрани трек"],
    "В избранное", "Медиа", priority=5,
)
def music_like(text):
    keyboard.send("f")
    return "Добавил в избранное"


@registry.command(
    ["дизлайк", "не нравится", "поставь дизлайк", "дизлайкни", "убери из рекомендаций",
     "не рекомендуй", "не хочу эту песню", "ужасная песня", "плохая песня",
     "надоела песня", "эта песня надоела"],
    "Дизлайк", "Медиа", priority=6,
)
def music_dislike(text):
    keyboard.send("d")
    return "Убрал из рекомендаций"


# ============================================================
#  СКРИНШОТ / СЕЛФИ / КАМЕРА
# ============================================================

@registry.command(
    ["скриншот", "сделай скрин", "заскринь", "сфоткай экран", "дай скрин", "скрин",
     "сделай скриншот", "скриншот экрана", "снимок экрана", "сделай снимок экрана",
     "сними экран", "запечатли экран", "принтскрин", "сфотографируй экран"],
    "Скриншот экрана", "Специальные", priority=6,
)
def make_screenshot(text):
    if not PIL_AVAILABLE:
        return "Библиотека Pillow не установлена"
    try:
        shot = ImageGrab.grab()
        fname = f"screenshot_{int(time.time())}.png"
        uploads = BASE_DIR / "uploads"
        uploads.mkdir(exist_ok=True)
        shot.save(uploads / fname)
        return f"Скриншот сохранён: /uploads/{fname}"
    except Exception as e:
        return f"Ошибка скриншота: {e}"


@registry.command(
    ["камера", "открой камеру", "включи камеру", "запусти камеру", "покажи камеру",
     "веб камера", "веб-камера", "вебка", "открой вебку"],
    "Открыть камеру", "Система", priority=5,
)
def open_camera(text):
    keyboard.send("win+4")
    return "Открываю камеру"


@registry.command(
    ["селфи", "сделай селфи", "сфоткай меня", "сделай фото", "сфотографируй меня",
     "сфоткай", "сними меня", "сделай фотку", "сделай снимок", "хочу селфи",
     "давай селфи", "сними фото"],
    "Сделать селфи", "Специальные",
)
def take_selfie(text):
    keyboard.send("win+2")

    def _snap():
        time.sleep(3)
        keyboard.send("space")

    threading.Timer(0, _snap).start()
    return "Улыбнитесь!"


# ============================================================
#  УМНЫЙ ДОМ (Яндекс)
# ============================================================

_HOME_MODULE_PATH = r"C:\Users\Yusuf\Programming\Python\libraries\yandex_smart_home\yandex_smart_home.py"
_DEFAULT_LIGHT = "Саске"
_home_instance = None


def _get_home():
    global _home_instance
    if _home_instance is not None:
        return _home_instance
    try:
        import importlib.util as _ilu
        import os as _os
        if not _os.path.exists(_HOME_MODULE_PATH):
            print(f"[smarthome] файл не найден: {_HOME_MODULE_PATH}")
            return None
        spec = _ilu.spec_from_file_location("yandex_smart_home", _HOME_MODULE_PATH)
        if spec is None or spec.loader is None:
            print("[smarthome] не удалось создать spec")
            return None
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _home_instance = mod.SmartHome()
        return _home_instance
    except Exception as e:
        print(f"[smarthome] не удалось загрузить модуль: {e}")
        return None


_DEVICE_STOP = {
    "лампу", "лампочку", "светильник", "устройство", "свет", "освещение",
    "включи", "выключи", "зажги", "погаси", "на", "у", "для", "пожалуйста",
    "верхний", "поставь", "установи", "сделай", "выставь", "измени",
}


def _extract_device(text, triggers, numeric=False):
    """Имя устройства из фразы: убираем триггеры и служебные слова
    (по словам, а не по буквам — иначе «Руслан» превращается в «Р слан»).
    numeric=True — число (яркость, температура) тоже не часть имени."""
    t = text.lower().strip()
    for tr in sorted(triggers, key=len, reverse=True):
        t = t.replace(tr, " ")
    words = [w for w in t.split()
             if w not in _DEVICE_STOP and not (numeric and w.isdigit())]
    return " ".join(words)


def _resolve_device(name):
    if not name:
        return _DEFAULT_LIGHT
    return name[0].upper() + name[1:]


@registry.command(
    _LIGHT_ON,
    "Умный дом: включить", "Умный дом", priority=8,
)
def light_on(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"
    triggers = _LIGHT_ON
    device = _resolve_device(_extract_device(text, triggers))
    try:
        home.device(device).turn_on()
        return f"Включаю {device}"
    except Exception as e:
        return f"Не удалось включить {device}: {e}"


@registry.command(
    _LIGHT_OFF,
    "Умный дом: выключить", "Умный дом", priority=8,
)
def light_off(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"
    triggers = _LIGHT_OFF
    device = _resolve_device(_extract_device(text, triggers))
    try:
        home.device(device).turn_off()
        return f"Выключаю {device}"
    except Exception as e:
        return f"Не удалось выключить {device}: {e}"


@registry.command(
    _BRIGHT,
    "Умный дом: яркость", "Умный дом", priority=8, followup="яркость {arg}",
)
def light_brightness(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"

    digits = "".join(filter(str.isdigit, text))
    if not digits:
        return "Скажите, например: яркость 50 на Саске"
    value = max(1, min(100, int(digits)))

    device = _resolve_device(_extract_device(text, _BRIGHT, numeric=True))
    try:
        home.device(device).turn_on()
        home.device(device).set_brightness(value)
        return f"Яркость {value}% на {device}"
    except Exception as e:
        return f"Не удалось поставить яркость: {e}"


@registry.command(
    _TEMP,
    "Умный дом: цветовая температура", "Умный дом", priority=8,
)
def light_temperature(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"

    digits = "".join(filter(str.isdigit, text))
    if not digits:
        return "Скажите, например: цветовая температура 4000"
    value = max(1500, min(9000, int(digits)))

    device = _resolve_device(_extract_device(text, _TEMP, numeric=True))
    try:
        home.device(device).turn_on()
        home.device(device).set_temperature(value)
        return f"Температура света {value}K на {device}"
    except Exception as e:
        return f"Не удалось поставить температуру: {e}"


@registry.command(
    _STATUS,
    "Умный дом: статус устройства", "Умный дом", priority=8,
)
def light_status(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"

    device = _resolve_device(_extract_device(text, _STATUS))

    try:
        d = home.device(device)
        info = d.get_status() if hasattr(d, "get_status") else None
        if info:
            return f"{device}: {info}"
        return f"{device} доступен"
    except Exception as e:
        return f"Не удалось получить статус {device}: {e}"


@registry.command(
    ["список устройств", "какие устройства", "мои устройства", "какие есть устройства",
     "покажи устройства", "умный дом", "что подключено", "мои лампы", "какие лампы"],
    "Умный дом: список устройств", "Умный дом", priority=8,
)
def smarthome_list(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"

    try:
        devices = None
        for attr in ("devices", "list_devices", "get_devices"):
            if hasattr(home, attr):
                v = getattr(home, attr)
                devices = v() if callable(v) else v
                break
        if not devices:
            return "Список устройств недоступен"
        names = [d if isinstance(d, str) else getattr(d, "name", str(d)) for d in devices]
        return "Устройства: " + ", ".join(names)
    except Exception as e:
        return f"Не удалось получить список: {e}"


# ============================================================
#  ХАОС
# ============================================================

chaos_active = False
chaos_thread = None
chaos_stop_event = threading.Event()


def _chaos_worker():
    while not chaos_stop_event.is_set():
        time.sleep(random.uniform(0.05, 0.2))
        action = random.randint(0, 10)
        try:
            if action == 0:
                mouse.move(random.randint(0, 1920), random.randint(0, 1080),
                           absolute=False, duration=0.01)
            elif action == 1:
                mouse.click("left")
            elif action == 2:
                mouse.click("right")
            elif action == 3:
                mouse.double_click("left")
            elif action == 4:
                mouse.wheel(random.randint(-3, 3))
            elif action == 5:
                keys = list("abcdefghijklmnopqrstuvwxyz0123456789") + \
                       ["space", "enter", "tab", "escape", "backspace", "delete"]
                keyboard.send(random.choice(keys))
            elif action == 6:
                keyboard.send("alt+tab")
                time.sleep(0.05)
            elif action == 7:
                try:
                    cur = _get_volume()
                    _set_volume(max(0.0, min(1.0, cur + random.uniform(-0.3, 0.3))))
                except Exception:
                    pass
            elif action == 8:
                keyboard.send(random.choice(["ctrl+c", "ctrl+v", "win+d", "win+e", "win+i", "alt+f4"]))
            elif action == 9:
                for i in range(5):
                    if chaos_stop_event.is_set():
                        break
                    o = i * 10
                    mouse.move(o, 0, absolute=False, duration=0.01)
                    mouse.move(0, o, absolute=False, duration=0.01)
                    mouse.move(-o, 0, absolute=False, duration=0.01)
                    mouse.move(0, -o, absolute=False, duration=0.01)
            elif action == 10:
                mouse.click("right")
                time.sleep(0.02)
                mouse.wheel(random.randint(-2, 2))
        except Exception as e:
            print(f"Chaos error: {e}")


@registry.command(
    ["хаос", "запусти хаос", "активируй хаос"],
    "Запустить хаос", "Специальные", priority=10, risky=True,
)
def start_chaos(text):
    global chaos_active, chaos_thread, chaos_stop_event
    if "стоп" in text or "останови" in text or "выключи" in text:
        if not chaos_active:
            return "Хаос не запущен"
        chaos_stop_event.set()
        chaos_active = False
        return "Хаос остановлен"
    if chaos_active:
        return "Хаос уже запущен"
    chaos_stop_event.clear()
    chaos_thread = threading.Thread(target=_chaos_worker, daemon=True)
    chaos_thread.start()
    chaos_active = True
    return "ХАОС АКТИВИРОВАН"


# ============================================================
#  СПЕЦИАЛЬНЫЕ
# ============================================================

@registry.command(
    _TR_EN,
    "Перевод RU→EN", "Специальные", priority=6,
)
def translate_en(text):
    query = _extract_query(text, _TR_EN)
    if not query:
        return "Что перевести?"
    if GIGACHAT_AVAILABLE and _gig is not None:
        try:
            ans = _gig.chat(f"Переведи на английский: {query}. Без объяснений.")
            return ans.strip() if ans else "Не удалось перевести"
        except Exception as e:
            print(f"[translate_en] {e}")
    webbrowser.open(f"https://translate.yandex.ru/?lang=ru-en&text={quote(query)}")
    return "Открываю переводчик"


@registry.command(
    _TR_RU,
    "Перевод EN→RU", "Специальные", priority=6,
)
def translate_ru(text):
    query = _extract_query(text, _TR_RU)
    if not query:
        return "Что перевести?"
    if GIGACHAT_AVAILABLE and _gig is not None:
        try:
            ans = _gig.chat(f"Переведи на русский: {query}. Без объяснений.")
            return ans.strip() if ans else "Не удалось перевести"
        except Exception as e:
            print(f"[translate_ru] {e}")
    webbrowser.open(f"https://translate.yandex.ru/?lang=en-ru&text={quote(query)}")
    return "Открываю переводчик"


@registry.command(
    _DRAW_WORDS,
    "Поиск картинок", "Специальные", priority=5,
)
def draw(text):
    query = _extract_query(text, _DRAW_WORDS)
    if not query:
        return "Что нарисовать?"
    webbrowser.open(f"https://yandex.ru/images/search?text={quote(query)}")
    return "Ищу изображения"


@registry.command(
    ["ухожу", "ушёл", "я ушёл", "ухожу спать", "я ушел", "я ухожу", "я ушла",
     "ушел", "пошёл спать", "пошел спать", "иду спать", "пойду спать"],
    "Выключить свет и ПК", "Специальные", priority=15, risky=True,
)
def leaving_home(text):
    home = _get_home()
    if home is not None:
        try:
            home.device(_DEFAULT_LIGHT).turn_off()
        except Exception as e:
            print(f"[leaving_home] свет: {e}")
    os.system("shutdown /s /t 10")
    return "Выключаю свет и компьютер. До свидания!"


@registry.command(
    _TIMER_WORDS,
    "Таймер", "Специальные", priority=5,
)
def set_timer(text):
    m = re.search(r"\d+", text)
    duration = m.group() if m else ""
    if duration:
        if os.path.exists(TIMER_PATH):
            subprocess.Popen([sys.executable, TIMER_PATH])
            time.sleep(2)
            keyboard.write(duration)
            keyboard.send("Enter")
            return f"Таймер на {duration} мин"
        return "Файл таймера не найден"
    return "На сколько минут?"


@registry.command(
    ["bluetooth", "блютуз", "включи блютуз", "выключи блютуз", "блютус", "включи блютус",
     "выключи блютус", "включи bluetooth", "выключи bluetooth", "переключи блютуз",
     "переключи bluetooth", "отключи блютуз"],
    "Bluetooth", "Специальные", risky=True,
)
def toggle_bluetooth(text):
    keyboard.send("win+a")
    time.sleep(0.3)
    keyboard.send("right")
    time.sleep(0.1)
    keyboard.send("enter")
    time.sleep(0.1)
    keyboard.send("win+a")
    return "Переключаю Bluetooth"


@registry.command(
    ["телефон", "позвони", "совершить звонок", "звонок", "позвонить", "сделай звонок",
     "совершить вызов", "хочу позвонить", "мне нужно позвонить"],
    "Позвонить", "Специальные", risky=True,
)
def call(text):
    keyboard.send("win+3")
    time.sleep(4)
    mouse.move(299, 180)
    time.sleep(0.1)
    mouse.click("left")
    time.sleep(0.1)
    mouse.move(350, 129)
    time.sleep(0.1)
    mouse.click("left")
    return "Звоню"


# ============================================================
#  КАТЕГОРИИ ДЛЯ САЙТА
# ============================================================

COMMAND_CATEGORIES = {
    "Основные": [
        "привет – поздороваться",
        "как дела – узнать состояние",
        "молодец – похвалить",
        "пока – попрощаться",
    ],
    "Интернет и поиск": [
        "найди [запрос] – поиск в Яндексе",
        "найди в ютубе [запрос] – видео на YouTube",
        "youtube – открыть YouTube",
        "погода – погода",
        "переводчик – открыть переводчик",
        "дипси – открыть DeepSeek",
        "игры яндекс – открыть Яндекс Игры",
    ],
    "Игры": [
        "камень ножницы бумага – запустить игру",
        "виселица – запустить игру",
        "викторина – запустить игру",
        "квест – запустить игру",
        "крестики-нолики – запустить игру",
        "угадай число – запустить игру",
    ],
    "Система": [
        "открой [приложение] – открыть программу",
        "закрой [приложение] – закрыть программу",
        "открой проводник – открыть файловый менеджер",
        "открой настройки – открыть настройки Windows",
        "сверни окно – свернуть окно",
        "закрой окно – закрыть окно",
        "браузер – открыть браузер",
        "вс код – открыть Visual Studio Code",
    ],
    "Мышь": [
        "мышь вверх – курсор вверх",
        "мышь вниз – курсор вниз",
        "мышь влево – курсор влево",
        "мышь вправо – курсор вправо",
        "левый клик – клик ЛКМ",
        "правый клик – клик ПКМ",
        "скролл вверх – прокрутить вверх",
        "скролл вниз – прокрутить вниз",
    ],
    "Клавиатура": [
        "напечатай [текст] – напечатать",
        "нажми клавишу [клавиша] – нажать",
    ],
    "Музыка": [
        "музыка [название] – поиск в Яндекс.Музыке",
        "моя волна – включить плейлист",
        "дальше – следующий трек",
        "пауза – пауза",
        "продолжи музыку – снять с паузы",
        "предыдущий – предыдущий трек",
        "лайк – добавить в избранное",
        "дизлайк – убрать из рекомендаций",
    ],
    "Громкость": [
        "громче – увеличить",
        "тише – уменьшить",
        "громкость [0-100] – установить",
    ],
    "Информация": [
        "время – текущее время",
        "дата – сегодняшняя дата",
        "батарея – состояние батареи",
    ],
    "Управление ПК": [
        "выключи компьютер – выключение через 10 сек",
        "перезагрузка – перезагрузка",
        "спящий режим – спящий режим",
        "заблокируй компьютер – блокировка",
        "отмени выключение – отменить выключение/перезагрузку",
    ],
    "Учёба": [
        "дз – домашнее задание",
        "оценки – оценки",
        "расписание – расписание на завтра",
    ],
    "Умный дом": [
        "включи свет – включить светильник",
        "выключи свет – выключить светильник",
        "яркость [0-100] – установить яркость",
        "цветовая температура [K] – установить",
        "статус лампы – узнать состояние",
        "список устройств – показать устройства",
    ],
    "Специальные": [
        "переведи на английский [текст] – перевод",
        "переведи на русский [текст] – перевод",
        "нарисуй [запрос] – поиск картинок",
        "скриншот – сделать скриншот экрана",
        "селфи – сделать снимок с камеры",
        "таймер [минуты] – запустить таймер",
        "телефон – позвонить",
        "bluetooth – переключить Bluetooth",
        "хаос – запустить хаос",
        "стоп хаос – остановить хаос",
        "ухожу – выключить свет и ПК",
    ],
}

FLAT_COMMANDS = []
for _cat, _cmds in COMMAND_CATEGORIES.items():
    for _cmd in _cmds:
        FLAT_COMMANDS.append(_cmd)