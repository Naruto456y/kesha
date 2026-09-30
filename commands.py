"""
Все команды проекта Кеша.
Каждая команда регистрируется через @registry.command.

Шаблон:
    @registry.command(patterns, description, category, priority)
    def my_command(text):
        # ... логика ...
        return "Что сказать пользователю"

Порядок имеет значение: специфичные команды (например, "открой проводник")
должны идти РАНЬШЕ общих ("открой") — иначе общая перехватит.
"""

from core import registry

import os
import time
import random
import webbrowser
import subprocess
from datetime import datetime, timedelta, date

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


def _r(lst):
    """Случайный элемент из списка."""
    return random.choice(lst)


def _launch_game(key):
    """Запуск игры из GAMES_PATHS."""
    path = GAMES_PATHS.get(key)
    if path and os.path.exists(path):
        try:
            subprocess.Popen(["python", path], shell=False)
            return "Запускаю игру"
        except Exception as e:
            return f"Ошибка запуска: {e}"
    return "Файл игры не найден"


def _get_volume():
    """Получить текущую громкость (0.0 – 1.0)."""
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
    """Установить громкость (0.0 – 1.0)."""
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


# ============================================================
#  ОСНОВНЫЕ КОМАНДЫ
# ============================================================

@registry.command(
    ["привет", "здравствуй", "хай", "добрый день", "доброе утро"],
    "Поздороваться", "Основные", priority=10,
)
def greeting(text):
    return _r(GREETINGS)


@registry.command(
    ["как дела", "как жизнь", "как настроение", "как ты"],
    "Узнать состояние", "Основные", priority=10,
)
def how_are_you(text):
    return "Всё отлично! Готов к работе."


@registry.command(
    ["молодец", "спасибо", "благодарю", "умница"],
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
    ["батарея", "заряд", "уровень заряда"],
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
    ["заблокируй компьютер", "блокировка", "заблокируй пк"],
    "Заблокировать ПК", "Система",
)
def lock_pc(text):
    os.system("rundll32.exe user32.dll,LockWorkStation")
    return "Экран заблокирован"


# ============================================================
#  ОКНА
# ============================================================

@registry.command(
    ["сверни", "свернуть окно", "сверни окно"],
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
    ["открой проводник", "проводник", "файловый менеджер"],
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


@registry.command(
    ["камера", "открой камеру"],
    "Открыть камеру", "Система", priority=5,
)
def open_camera(text):
    keyboard.send("win+2")
    return "Открываю камеру"


# ============================================================
#  ГРОМКОСТЬ (pycaw)
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
#  ПОИСК И ИНТЕРНЕТ
# ============================================================

@registry.command(
    ["найди в ютуби", "поищи в ютубе", "видео в ютубе", "найди в ютубе"],
    "Поиск на YouTube", "Интернет", priority=5,
)
def search_youtube(text):
    query = text
    for w in ["найди в ютуби", "поищи в ютубе", "видео в ютубе", "найди в ютубе"]:
        query = query.replace(w, "")
    query = query.strip()
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
    ["найди", "поищи", "погугли", "загугли"],
    "Поиск в интернете", "Интернет",
)
def search_web(text):
    query = text
    for w in ["найди", "поищи", "погугли", "загугли"]:
        query = query.replace(w, "")
    query = query.strip()
    if not query:
        return "Что искать?"
    webbrowser.open(f"https://yandex.ru/search/?text={query}")
    return _r(SEARCH_RESPONSES)


@registry.command(
    ["youtube", "ютуб", "открой ютуб"],
    "Открыть YouTube", "Интернет", priority=5,
)
def open_youtube(text):
    webbrowser.open("https://youtube.com")
    return _r(OK_RESPONSES)


@registry.command(
    ["погода", "температура на улице", "какая погода"],
    "Узнать погоду", "Интернет",
)
def get_weather(text):
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
    ["дипси", "deepseek", "открой дипси"],
    "Открыть DeepSeek", "Интернет", priority=5,
)
def open_deepseek(text):
    webbrowser.open("https://chat.deepseek.com/")
    return "Открываю DeepSeek"


@registry.command(
    ["игры яндекс", "яндекс игры", "игры"],
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
    ["расписание", "расписание на завтра"],
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
    ["браузер", "открой браузер"],
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
    ["открой"],
    "Открыть приложение", "Система",
)
def open_app(text):
    # исключения, которые обрабатываются другими командами
    skip = [
        "проводник", "настройки", "roblox", "роблокс",
        "minecraft", "майн", "камер", "селфи", "браузер", "яндекс",
        "ютуб", "youtube", "дипси", "deepseek", "переводчик",
        "игры", "музык", "вол", "избр",
    ]
    if any(s in text for s in skip):
        return None

    app = text.replace("открой", "").strip()
    if not app:
        return "Что открыть?"

    # 1. Ищем в APP_PATHS
    for key, path in APP_PATHS.items():
        if key in app or app in key:
            if os.path.exists(path):
                try:
                    os.startfile(path)
                    return f"Открываю {app}"
                except Exception:
                    pass

    # 2. Fallback на AppOpener
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
#  ИГРЫ (из GAMES_PATHS)
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
#  МЕДИА (музыка, управление треками через клавиши Яндекс.Музыки)
# ============================================================

@registry.command(
    ["музыка", "включи музыку", "поставь музыку"],
    "Включить музыку", "Медиа",
)
def play_music(text):
    query = text
    for w in ["музыка", "включи музыку", "поставь музыку", "включи", "поставь"]:
        query = query.replace(w, "")
    query = query.strip()
    if query:
        try:
            AppOpener.open("Yandex", True)
            webbrowser.open(
                f"https://music.yandex.ru/search?text={query.replace(' ', '+')}"
            )
            return f"Ищу: {query}"
        except Exception:
            return "Ошибка запуска музыки"
    webbrowser.open("https://music.yandex.ru/")
    return "Открываю Яндекс.Музыку"


@registry.command(
    ["моя волна", "волну", "избранное", "мою волну"],
    "Моя волна", "Медиа",
)
def play_wave(text):
    try:
        AppOpener.open("Yandex", True)
        webbrowser.open("https://music.yandex.ru/")
        time.sleep(2)
        keyboard.send("K")
        return "Включаю мою волну"
    except Exception:
        return "Ошибка"


@registry.command(
    ["пауза", "стоп музыка", "заткнись", "выключи музыку"],
    "Пауза", "Медиа",
)
def music_pause(text):
    keyboard.send("K")
    return "Пауза"


@registry.command(
    ["дальше", "следующий трек", "некст", "следующая песня"],
    "Следующий трек", "Медиа",
)
def music_next(text):
    keyboard.send("N")
    return "Следующий"


@registry.command(
    ["предыдущий", "прошлый трек", "предыдущая песня"],
    "Предыдущий трек", "Медиа",
)
def music_prev(text):
    keyboard.send("P")
    return "Предыдущий"


@registry.command(
    ["лайк", "нравится", "мне нравится"],
    "В избранное", "Медиа",
)
def music_like(text):
    keyboard.send("F")
    return "Добавил в избранное"


@registry.command(
    ["дизлайк", "не нравится"],
    "Дизлайк", "Медиа",
)
def music_dislike(text):
    keyboard.send("D")
    return "Убрал из рекомендаций"


# ============================================================
#  МЫШЬ И КЛАВИАТУРА
# ============================================================

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


@registry.command(["вниз"], "Скролл вниз", "Система")
def scroll_down(text):
    mouse.wheel(-1)
    return ""


@registry.command(["верх"], "Скролл вверх", "Система")
def scroll_up(text):
    mouse.wheel(1)
    return ""


@registry.command(
    ["напечатай", "напиши"],
    "Напечатать текст", "Система",
)
def type_text(text):
    t = text
    for w in ["напечатай", "напиши"]:
        t = t.replace(w, "")
    t = t.strip()
    if t:
        keyboard.write(t)
        return f"Напечатал: {t}"
    return "Что напечатать?"


@registry.command(
    ["нажми клавишу", "нажми"],
    "Нажать клавишу", "Система",
)
def press_key(text):
    key = text
    for w in ["нажми клавишу", "нажми"]:
        key = key.replace(w, "")
    key = key.strip()
    if key:
        keyboard.send(key)
        return f"Нажал {key}"
    return "Какую клавишу?"


# ============================================================
#  СПЕЦИАЛЬНЫЕ
# ============================================================

@registry.command(
    ["переведи на английский"],
    "Перевод RU→EN", "Специальные",
)
def translate_en(text):
    query = text.replace("переведи на английский", "").strip()
    if not query:
        return "Что перевести?"
    webbrowser.open(f"https://translate.yandex.ru/?lang=ru-en&text={query}")
    return "Открываю переводчик"


@registry.command(
    ["переведи на русский"],
    "Перевод EN→RU", "Специальные",
)
def translate_ru(text):
    query = text.replace("переведи на русский", "").strip()
    if not query:
        return "Что перевести?"
    webbrowser.open(f"https://translate.yandex.ru/?lang=en-ru&text={query}")
    return "Открываю переводчик"


@registry.command(
    ["нарисуй", "покажи картинку", "покажи изображение"],
    "Поиск картинок", "Специальные",
)
def draw(text):
    query = text
    for w in ["нарисуй", "покажи картинку", "покажи изображение", "изображение"]:
        query = query.replace(w, "")
    query = query.strip()
    if not query:
        return "Что нарисовать?"
    webbrowser.open(f"https://yandex.ru/images/search?text={query}")
    return "Ищу изображения"


@registry.command(
    ["включи свет", "включи светильник"],
    "Умный дом: свет вкл", "Специальные",
)
def light_on(text):
    webbrowser.open("https://alice.yandex.ru/")
    time.sleep(2)
    keyboard.write("Включи светильник")
    keyboard.send("Enter")
    return "Свет включён"


@registry.command(
    ["выключи свет", "выключи светильник"],
    "Умный дом: свет выкл", "Специальные",
)
def light_off(text):
    webbrowser.open("https://alice.yandex.ru/")
    time.sleep(2)
    keyboard.write("Выключи светильник")
    keyboard.send("Enter")
    return "Свет выключен"


@registry.command(
    ["ухожу", "ушёл", "я ушёл", "ухожу спать", "я ушел"],
    "Выключить свет и ПК", "Специальные", priority=15,
)
def leaving_home(text):
    webbrowser.open("https://alice.yandex.ru/")
    time.sleep(2)
    keyboard.write("Выключи светильник")
    keyboard.send("Enter")
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
            subprocess.Popen(["python", TIMER_PATH])
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
    ["телефон", "позвони", "совершить звонок"],
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


@registry.command(
    ["селфи", "сделай селфи", "сфоткай меня"],
    "Сделать селфи", "Специальные",
)
def take_selfie(text):
    keyboard.send("win+2")
    time.sleep(2)
    msg = "Улыбнитесь!"
    time.sleep(1.5)
    keyboard.send("space")
    return msg