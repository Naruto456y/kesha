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

from help_manager import ImportManager as _im

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
    for w in words:
        q = q.replace(w, "")
    return q.strip()


# ============================================================
#  ОСНОВНЫЕ
# ============================================================

@registry.command(
    ["привет", "здравствуй", "хай", "добрый день", "доброе утро", "приветствую", "здарова"],
    "Поздороваться", "Основные", priority=10,
)
def greeting(text):
    return _r(GREETINGS)


@registry.command(
    ["как дела", "как жизнь", "как настроение", "как ты", "как поживаешь"],
    "Узнать состояние", "Основные", priority=10,
)
def how_are_you(text):
    return "Всё отлично! Готов к работе."


@registry.command(
    ["молодец", "спасибо", "благодарю", "умница", "красава"],
    "Похвалить", "Основные", priority=10,
)
def thanks(text):
    return _r(THANKS_RESPONSES)


@registry.command(
    ["пока", "выход", "выключись", "до свидания", "прощай"],
    "Попрощаться", "Основные", priority=20,
)
def goodbye(text):
    return "До свидания!"


# ============================================================
#  СИСТЕМНАЯ ИНФОРМАЦИЯ
# ============================================================

@registry.command(
    ["время", "который час", "сколько времени"],
    "Текущее время", "Система",
)
def get_time(text):
    return f"Сейчас {datetime.now().strftime('%H:%M')}"


@registry.command(
    ["дата", "какое сегодня число", "какой сегодня день"],
    "Текущая дата", "Система",
)
def get_date(text):
    return f"Сегодня {datetime.now().strftime('%d.%m.%Y')}"


@registry.command(
    ["батарея", "заряд", "уровень заряда", "состояние батареи"],
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
    ["выключи компьютер", "шатдаун", "выруби компьютер"],
    "Выключить ПК", "Система",
)
def shutdown_pc(text):
    os.system("shutdown /s /t 10")
    return "Выключаю компьютер через 10 секунд"


@registry.command(
    ["перезагрузка", "перезагрузи компьютер", "ребут", "рестарт"],
    "Перезагрузить ПК", "Система",
)
def restart_pc(text):
    os.system("shutdown /r /t 5")
    return "Перезагружаю компьютер"


@registry.command(
    ["спящий режим", "уснуть", "спать", "сон"],
    "Спящий режим", "Система",
)
def sleep_pc(text):
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "Ухожу в спящий режим"


@registry.command(
    ["заблокируй компьютер", "блокировка", "заблокируй пк", "блокни"],
    "Заблокировать ПК", "Система",
)
def lock_pc(text):
    os.system("rundll32.exe user32.dll,LockWorkStation")
    return "Экран заблокирован"


# ============================================================
#  ОКНА
# ============================================================

@registry.command(
    ["сверни окно", "сверни", "свернуть окно"],
    "Свернуть окно", "Система",
)
def minimize_window(text):
    keyboard.send("win+down")
    return _r(OK_RESPONSES)


@registry.command(
    ["закрой окно"],
    "Закрыть окно", "Система", priority=5,
)
def close_window(text):
    keyboard.send("alt+f4")
    return _r(OK_RESPONSES)


@registry.command(
    ["открой проводник", "проводник", "файловый менеджер", "папка"],
    "Открыть проводник", "Система", priority=5,
)
def open_explorer(text):
    keyboard.send("win+e")
    return "Проводник открыт"


@registry.command(
    ["открой настройки", "настройки", "параметры"],
    "Открыть настройки", "Система", priority=5,
)
def open_settings(text):
    keyboard.send("win+i")
    return "Настройки открыты"


# ============================================================
#  ГРОМКОСТЬ
# ============================================================

@registry.command(
    ["громче", "увеличь громкость", "прибавь громкость"],
    "Громкость +", "Медиа", priority=5,
)
def volume_up(text):
    new = min(1.0, _get_volume() + 0.1)
    _set_volume(new)
    return f"Громкость {int(new * 100)}%"


@registry.command(
    ["тише", "уменьши громкость", "сбавь громкость"],
    "Громкость −", "Медиа", priority=5,
)
def volume_down(text):
    new = max(0.0, _get_volume() - 0.1)
    _set_volume(new)
    return f"Громкость {int(new * 100)}%"


@registry.command(
    ["громкость", "поставь громкость", "установи громкость"],
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

@registry.command(
    ["мышь вверх", "курсор вверх"],
    "Мышь вверх", "Система", priority=5,
)
def mouse_up(text):
    mouse.move(0, -50, absolute=False, duration=0.1)
    return "Мышь вверх"


@registry.command(
    ["мышь вниз", "курсор вниз"],
    "Мышь вниз", "Система", priority=5,
)
def mouse_down(text):
    mouse.move(0, 50, absolute=False, duration=0.1)
    return "Мышь вниз"


@registry.command(
    ["мышь влево", "курсор влево"],
    "Мышь влево", "Система", priority=5,
)
def mouse_left(text):
    mouse.move(-50, 0, absolute=False, duration=0.1)
    return "Мышь влево"


@registry.command(
    ["мышь вправо", "курсор вправо"],
    "Мышь вправо", "Система", priority=5,
)
def mouse_right(text):
    mouse.move(50, 0, absolute=False, duration=0.1)
    return "Мышь вправо"


@registry.command(
    ["левый клик", "левый", "лкм"],
    "ЛКМ", "Система",
)
def click_left(text):
    mouse.click("left")
    return "Левый клик"


@registry.command(
    ["правый клик", "правый", "пкм"],
    "ПКМ", "Система",
)
def click_right(text):
    mouse.click("right")
    return "Правый клик"


@registry.command(
    ["скролл вниз", "прокрути вниз", "пролистай вниз"],
    "Скролл вниз", "Система", priority=5,
)
def scroll_down(text):
    mouse.wheel(-3)
    return "Скролл вниз"


@registry.command(
    ["скролл вверх", "прокрути вверх", "пролистай вверх"],
    "Скролл вверх", "Система", priority=5,
)
def scroll_up(text):
    mouse.wheel(3)
    return "Скролл вверх"


# ============================================================
#  КЛАВИАТУРА
# ============================================================

@registry.command(
    ["напечатай", "напиши"],
    "Напечатать текст", "Система",
)
def type_text(text):
    t = _extract_query(text, ["напечатай", "напиши"])
    if t:
        keyboard.write(t)
        return f"Напечатал: {t}"
    return "Что напечатать?"


@registry.command(
    ["нажми клавишу", "нажми"],
    "Нажать клавишу", "Система",
)
def press_key(text):
    key = _extract_query(text, ["нажми клавишу", "нажми"])
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
    ["найди в ютуби", "поищи в ютубе", "видео в ютубе", "найди в ютубе"],
    "Поиск на YouTube", "Интернет", priority=5,
)
def search_youtube(text):
    query = _extract_query(text, ["найди в ютуби", "поищи в ютубе", "видео в ютубе", "найди в ютубе"])
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
    ["найди", "поищи", "погугли", "загугли", "поиск"],
    "Поиск в интернете", "Интернет",
)
def search_web(text):
    query = _extract_query(text, ["найди", "поищи", "погугли", "загугли", "поиск"])
    if not query:
        return "Что искать?"
    webbrowser.open(f"https://yandex.ru/search/?text={quote(query)}")
    return _r(SEARCH_RESPONSES)


@registry.command(
    ["youtube", "ютуб", "открой ютуб"],
    "Открыть YouTube", "Интернет", priority=5,
)
def open_youtube(text):
    webbrowser.open("https://youtube.com")
    return _r(OK_RESPONSES)


@registry.command(
    ["погода", "температура на улице", "какая погода", "что на улице"],
    "Узнать погоду", "Интернет",
)
def get_weather_cmd(text):
    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={WEATHER_CITY}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
        )
        r = requests.get(url, timeout=10).json()
        temp = r["main"]["temp"]
        desc = r["weather"][0]["description"]
        return f"В {WEATHER_CITY}: {temp}°C, {desc}"
    except Exception as e:
        return f"Ошибка погоды: {e}"


@registry.command(
    ["переводчик", "открой переводчик"],
    "Открыть переводчик", "Интернет", priority=5,
)
def open_translator(text):
    webbrowser.open("https://translate.yandex.ru/")
    return _r(OK_RESPONSES)


@registry.command(
    ["дипси", "deepseek", "чат gpt"],
    "Открыть DeepSeek", "Интернет", priority=5,
)
def open_deepseek(text):
    webbrowser.open("https://chat.deepseek.com/")
    return "Открываю DeepSeek"


@registry.command(
    ["игры яндекс", "яндекс игры", "поиграть"],
    "Открыть Яндекс Игры", "Интернет", priority=5,
)
def open_yandex_games(text):
    webbrowser.open("https://yandex.ru/games/")
    return "Открываю Яндекс Игры"


# ============================================================
#  УЧЁБА
# ============================================================

@registry.command(
    ["дз", "домашнее задание", "домашка", "домашку"],
    "ДЗ", "Учёба",
)
def school_homework(text):
    webbrowser.open("https://school.mos.ru/diary/homeworks/")
    return "Открываю домашнее задание"


@registry.command(
    ["оценки", "отметки", "мои оценки"],
    "Оценки", "Учёба",
)
def school_marks(text):
    webbrowser.open("https://school.mos.ru/diary/marks/current-marks")
    return "Показываю оценки"


@registry.command(
    ["расписание", "расписание на завтра", "уроки на завтра"],
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
    ["открой minecraft", "открой майнкрафт", "майн", "майнкрафт"],
    "Запустить Minecraft", "Игры", priority=5,
)
def open_minecraft(text):
    path = APP_PATHS.get("майнкрафт")
    if path and os.path.exists(path):
        os.startfile(path)
        return "Открываю Minecraft"
    return "Не нашёл Minecraft"


@registry.command(
    ["открой roblox", "роблокс", "открой роблокс"],
    "Запустить Roblox", "Игры", priority=5,
)
def open_roblox(text):
    path = APP_PATHS.get("роблокс")
    if path and os.path.exists(path):
        os.startfile(path)
        return "Открываю Roblox"
    return "Не нашёл Roblox"


@registry.command(
    ["браузер", "открой браузер", "интернет", "яндекс"],
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
    ["открой вс код", "открой visual studio code", "открой vs code", "открой визуалку"],
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
    ["открой"],
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

    app = text.replace("открой", "").strip()
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
    ["закрой"],
    "Закрыть приложение", "Система",
)
def close_app(text):
    app = text.replace("закрой", "").strip()
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
    ["камень ножницы бумага", "камень ножницы"],
    "Игра: КНБ", "Игры",
)
def game_rps(text):
    return _launch_game("камень ножницы бумага")


@registry.command(["виселица"], "Игра: Виселица", "Игры")
def game_hangman(text):
    return _launch_game("виселица")


@registry.command(["викторина"], "Игра: Викторина", "Игры")
def game_quiz(text):
    return _launch_game("викторина")


@registry.command(["квест"], "Игра: Квест", "Игры")
def game_quest(text):
    return _launch_game("квест")


@registry.command(
    ["крестики-нолики", "крестики нолики"],
    "Игра: Крестики-нолики", "Игры",
)
def game_tictactoe(text):
    return _launch_game("крестики-нолики")


@registry.command(["угадай число"], "Игра: Угадай число", "Игры")
def game_guess(text):
    return _launch_game("угадай число")


# ============================================================
#  МЕДИА
# ============================================================

@registry.command(
    ["музыка", "включи музыку", "поставь музыку", "музон", "трек", "песня"],
    "Включить музыку", "Медиа",
)
def play_music(text):
    query = _extract_query(text, ["включи музыку", "поставь музыку", "музыка", "музон", "трек", "песня"])
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
    ["моя волна", "волну", "избранное", "мою волну", "любимое"],
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
    ["пауза", "стоп музыка", "заткнись", "выключи музыку"],
    "Пауза", "Медиа",
)
def music_pause(text):
    keyboard.send("k")
    return "Пауза"


@registry.command(
    ["дальше", "следующий трек", "некст", "следующая песня"],
    "Следующий трек", "Медиа",
)
def music_next(text):
    keyboard.send("n")
    return "Следующий"


@registry.command(
    ["предыдущий", "прошлый трек", "предыдущая песня"],
    "Предыдущий трек", "Медиа",
)
def music_prev(text):
    keyboard.send("p")
    return "Предыдущий"


@registry.command(
    ["лайк", "нравится", "мне нравится"],
    "В избранное", "Медиа",
)
def music_like(text):
    keyboard.send("f")
    return "Добавил в избранное"


@registry.command(
    ["дизлайк", "не нравится"],
    "Дизлайк", "Медиа",
)
def music_dislike(text):
    keyboard.send("d")
    return "Убрал из рекомендаций"


# ============================================================
#  СКРИНШОТ / СЕЛФИ / КАМЕРА
# ============================================================

@registry.command(
    ["скриншот", "сделай скрин", "заскринь", "сфоткай экран", "дай скрин"],
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
    ["камера", "открой камеру"],
    "Открыть камеру", "Система", priority=5,
)
def open_camera(text):
    keyboard.send("win+2")
    return "Открываю камеру"


@registry.command(
    ["селфи", "сделай селфи", "сфоткай меня", "сделай фото"],
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
        mod = _im.import_module(_HOME_MODULE_PATH)
        _home_instance = mod.SmartHome()
        return _home_instance
    except Exception as e:
        print(f"[smarthome] не удалось загрузить модуль: {e}")
        return None


def _extract_device(text, triggers):
    t = text.lower().strip()
    for tr in triggers:
        t = t.replace(tr, " ")
    for w in ["лампу", "лампочку", "светильник", "устройство", "свет",
              "включи", "выключи", "зажги", "погаси", "на", "у", "для"]:
        t = t.replace(w, " ")
    return " ".join(t.split()).strip()


def _resolve_device(name):
    if not name:
        return _DEFAULT_LIGHT
    return name[0].upper() + name[1:]


@registry.command(
    ["включи лампу", "включи свет", "включи светильник", "включи лампочку", "зажги свет"],
    "Умный дом: включить", "Умный дом", priority=8,
)
def light_on(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"
    triggers = ["включи лампу", "включи свет", "включи светильник", "включи лампочку", "зажги свет"]
    device = _resolve_device(_extract_device(text, triggers))
    try:
        home.device(device).turn_on()
        return f"Включаю {device}"
    except Exception as e:
        return f"Не удалось включить {device}: {e}"


@registry.command(
    ["выключи лампу", "выключи свет", "выключи светильник", "выключи лампочку", "погаси свет"],
    "Умный дом: выключить", "Умный дом", priority=8,
)
def light_off(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"
    triggers = ["выключи лампу", "выключи свет", "выключи светильник", "выключи лампочку", "погаси свет"]
    device = _resolve_device(_extract_device(text, triggers))
    try:
        home.device(device).turn_off()
        return f"Выключаю {device}"
    except Exception as e:
        return f"Не удалось выключить {device}: {e}"


@registry.command(
    ["яркость", "поставь яркость", "установи яркость", "сделай яркость"],
    "Умный дом: яркость", "Умный дом", priority=8,
)
def light_brightness(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"

    digits = "".join(filter(str.isdigit, text))
    if not digits:
        return "Скажите, например: яркость 50 на Саске"
    value = max(1, min(100, int(digits)))

    triggers = ["поставь яркость", "установи яркость", "сделай яркость", "яркость"]
    device = _resolve_device(_extract_device(text, triggers))
    try:
        home.device(device).turn_on()
        home.device(device).set_brightness(value)
        return f"Яркость {value}% на {device}"
    except Exception as e:
        return f"Не удалось поставить яркость: {e}"


@registry.command(
    ["цветовая температура", "температура света", "поставь температуру света",
     "поставь цветовую температуру", "установи цветовую температуру"],
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

    triggers = ["поставь цветовую температуру", "установи цветовую температуру",
                "поставь температуру света", "цветовая температура", "температура света"]
    device = _resolve_device(_extract_device(text, triggers))
    try:
        home.device(device).turn_on()
        home.device(device).set_temperature(value)
        return f"Температура света {value}K на {device}"
    except Exception as e:
        return f"Не удалось поставить температуру: {e}"


@registry.command(
    ["статус лампы", "статус света", "статус светильника"],
    "Умный дом: статус устройства", "Умный дом", priority=8,
)
def light_status(text):
    home = _get_home()
    if home is None:
        return "Модуль умного дома недоступен"

    triggers = ["статус лампы", "статус света", "статус светильника"]
    device = _resolve_device(_extract_device(text, triggers))

    try:
        d = home.device(device)
        info = d.get_status() if hasattr(d, "get_status") else None
        if info:
            return f"{device}: {info}"
        return f"{device} доступен"
    except Exception as e:
        return f"Не удалось получить статус {device}: {e}"


@registry.command(
    ["список устройств", "какие устройства", "мои устройства"],
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
    "Запустить хаос", "Специальные", priority=10,
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
    ["переведи на английский"],
    "Перевод RU→EN", "Специальные", priority=6,
)
def translate_en(text):
    query = text.replace("переведи на английский", "").strip()
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
    ["переведи на русский"],
    "Перевод EN→RU", "Специальные", priority=6,
)
def translate_ru(text):
    query = text.replace("переведи на русский", "").strip()
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
    ["нарисуй", "покажи картинку", "покажи изображение", "изображение"],
    "Поиск картинок", "Специальные",
)
def draw(text):
    query = _extract_query(text, ["нарисуй", "покажи картинку", "покажи изображение", "изображение"])
    if not query:
        return "Что нарисовать?"
    webbrowser.open(f"https://yandex.ru/images/search?text={quote(query)}")
    return "Ищу изображения"


@registry.command(
    ["ухожу", "ушёл", "я ушёл", "ухожу спать", "я ушел"],
    "Выключить свет и ПК", "Специальные", priority=15,
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
    ["таймер", "поставь таймер", "засеки время"],
    "Таймер", "Специальные",
)
def set_timer(text):
    duration = text
    for w in ["поставь таймер на", "поставь таймер", "таймер", "засеки время"]:
        duration = duration.replace(w, "")
    duration = (
        duration.replace("минуту", "")
        .replace("минут", "")
        .replace("минуты", "")
        .replace("ы", "")
        .strip()
    )
    if duration.isdigit():
        if os.path.exists(TIMER_PATH):
            subprocess.Popen([sys.executable, TIMER_PATH])
            time.sleep(2)
            keyboard.write(duration)
            keyboard.send("Enter")
            return f"Таймер на {duration} мин"
        return "Файл таймера не найден"
    return "На сколько минут?"


@registry.command(
    ["bluetooth", "блютуз", "включи блютуз", "выключи блютуз"],
    "Bluetooth", "Специальные",
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
    ["телефон", "позвони", "совершить звонок", "звонок"],
    "Позвонить", "Специальные",
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