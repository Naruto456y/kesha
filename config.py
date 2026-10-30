"""
Все настройки проекта Кеша.
Все пути, токены, фразы и константы.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ============================================================
#  БАЗОВЫЕ ПУТИ
# ============================================================
BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / "Media"
UPLOAD_DIR = BASE_DIR / "uploads"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

UPLOAD_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ============================================================
#  ПУТИ К ИГРАМ (автопоиск: Media/games/ или Media/)
# ============================================================
_games_subdir = MEDIA_DIR / "games"
GAMES_DIR = _games_subdir if _games_subdir.exists() else MEDIA_DIR

GAMES_PATHS = {
    "камень ножницы бумага": str(GAMES_DIR / "stone_knots_paper.py"),
    "виселица":              str(GAMES_DIR / "hangman.py"),
    "викторина":             str(GAMES_DIR / "quiz.py"),
    "квест":                 str(GAMES_DIR / "Quest_act.py"),
    "крестики-нолики":       str(GAMES_DIR / "tictactoe.py"),
    "угадай число":          str(GAMES_DIR / "rand_game.py"),
}

# ============================================================
#  ПУТИ К ПРИЛОЖЕНИЯМ (ярлыки рабочего стола)
# ============================================================
APP_PATHS = {
    # ============ ОСНОВНЫЕ ============
    "творчество":         r"C:\Users\Yusuf\Desktop\Творчество.lnk",
    "текстовый документ": r"C:\Users\Yusuf\Desktop\Текстовый документ.txt",
    "заметка":            r"C:\Users\Yusuf\Desktop\Текстовый документ.txt",
    "блокнот":            r"C:\Users\Yusuf\Desktop\Блокнот.lnk",
    "notepad":            r"C:\Users\Yusuf\Desktop\Блокнот.lnk",
    "записки":            r"C:\Users\Yusuf\Desktop\Записки.lnk",
    "диктофон":           r"C:\Users\Yusuf\Desktop\Диктофон.lnk",
    "запись голоса":      r"C:\Users\Yusuf\Desktop\Диктофон.lnk",
    "терминал":           r"C:\Users\Yusuf\Desktop\Терминал.lnk",
    "командная строка":   r"C:\Users\Yusuf\Desktop\Терминал.lnk",
    "terminal":           r"C:\Users\Yusuf\Desktop\Терминал.lnk",
    "фотографии":         r"C:\Users\Yusuf\Desktop\Фотографии.lnk",
    "фото":               r"C:\Users\Yusuf\Desktop\Фотографии.lnk",
    "часы":               r"C:\Users\Yusuf\Desktop\Часы.lnk",
    "камера":             r"C:\Users\Yusuf\Desktop\Камера.lnk",
    "селфи":              r"C:\Users\Yusuf\Desktop\Камера.lnk",
    "настройки":          r"C:\Users\Yusuf\Desktop\Настройки.lnk",

    # ============ МУЗЫКА И МЕДИА ============
    "яндекс музыка":      r"C:\Users\Yusuf\Desktop\Яндекс Музыка.lnk",
    "музыка":             r"C:\Users\Yusuf\Desktop\Яндекс Музыка.lnk",
    "yandex music":       r"C:\Users\Yusuf\Desktop\Яндекс Музыка.lnk",
    "клипчамп":           r"C:\Users\Yusuf\Desktop\Microsoft Clipchamp.lnk",
    "clipchamp":          r"C:\Users\Yusuf\Desktop\Microsoft Clipchamp.lnk",
    "видеоредактор":      r"C:\Users\Yusuf\Desktop\Microsoft Clipchamp.lnk",
    "кап кут":            r"C:\Users\Yusuf\Desktop\CapCut.lnk",
    "capcut":             r"C:\Users\Yusuf\Desktop\CapCut.lnk",
    "мовавика":           r"C:\Users\Yusuf\Desktop\Мовавика.lnk",
    "мовави":             r"C:\Users\Yusuf\Desktop\Мовавика.lnk",

    # ============ ГРАФИКА И 3D ============
    "блендер":            r"C:\Users\Yusuf\Desktop\Blender 4.2.lnk",
    "blender":            r"C:\Users\Yusuf\Desktop\Blender 4.2.lnk",
    "3д моделирование":   r"C:\Users\Yusuf\Desktop\Blender 4.2.lnk",
    "гимп":               r"C:\Users\Yusuf\Desktop\GIMP 3.0.4.lnk",
    "gimp":               r"C:\Users\Yusuf\Desktop\GIMP 3.0.4.lnk",
    "фотошоп":            r"C:\Users\Yusuf\Desktop\GIMP 3.0.4.lnk",
    "фрикад":             r"C:\Users\Yusuf\Desktop\FreeCAD 1.1.lnk",
    "freecad":            r"C:\Users\Yusuf\Desktop\FreeCAD 1.1.lnk",
    "паинт":              r"C:\Users\Yusuf\Desktop\Paint.lnk",
    "пейнт":              r"C:\Users\Yusuf\Desktop\Paint.lnk",
    "рисовалка":          r"C:\Users\Yusuf\Desktop\Paint.lnk",
    "пиксарт":            r"C:\Users\Yusuf\Desktop\Picsart - Photo Studio.lnk",
    "picsart":            r"C:\Users\Yusuf\Desktop\Picsart - Photo Studio.lnk",

    # ============ ОФИС ============
    "офис":               r"C:\Users\Yusuf\Desktop\Neat Office.lnk",
    "документы":          r"C:\Users\Yusuf\Desktop\Neat Office.lnk",
    "эксель":             r"C:\Users\Yusuf\Desktop\Excel.lnk",
    "excel":              r"C:\Users\Yusuf\Desktop\Excel.lnk",
    "ворд":               r"C:\Users\Yusuf\Desktop\Word.lnk",
    "word":               r"C:\Users\Yusuf\Desktop\Word.lnk",
    "паверпоинт":         r"C:\Users\Yusuf\Desktop\PowerPoint.lnk",
    "powerpoint":         r"C:\Users\Yusuf\Desktop\PowerPoint.lnk",

    # ============ РАЗРАБОТКА ============
    "вс код":             r"C:\Users\Yusuf\Desktop\Visual Studio Code.lnk",
    "visual studio code": r"C:\Users\Yusuf\Desktop\Visual Studio Code.lnk",
    "vs code":            r"C:\Users\Yusuf\Desktop\Visual Studio Code.lnk",
    "визуалка":           r"C:\Users\Yusuf\Desktop\Visual Studio Code.lnk",
    "гитхаб":             r"C:\Users\Yusuf\Desktop\GitHub Desktop.lnk",
    "github":             r"C:\Users\Yusuf\Desktop\GitHub Desktop.lnk",
    "гит":                r"C:\Users\Yusuf\Desktop\GitHub Desktop.lnk",
    "клод":               r"C:\Users\Yusuf\Desktop\Claude.lnk",
    "claude":             r"C:\Users\Yusuf\Desktop\Claude.lnk",
    "пайтон":             r"C:\Users\Yusuf\Desktop\Python 3.13 (64-bit).lnk",
    "python":             r"C:\Users\Yusuf\Desktop\Python 3.13 (64-bit).lnk",

    # ============ БРАУЗЕРЫ ============
    "яндекс":             r"C:\Users\Yusuf\Desktop\Yandex.lnk",
    "яндекс браузер":     r"C:\Users\Yusuf\Desktop\Yandex.lnk",
    "yandex":             r"C:\Users\Yusuf\Desktop\Yandex.lnk",
    "браузер":            r"C:\Users\Yusuf\Desktop\Yandex.lnk",
    "майкрософт стор":    r"C:\Users\Yusuf\Desktop\Microsoft Store.lnk",
    "microsoft store":    r"C:\Users\Yusuf\Desktop\Microsoft Store.lnk",
    "стор":               r"C:\Users\Yusuf\Desktop\Microsoft Store.lnk",

    # ============ ИГРЫ ============
    "роблокс":            r"C:\Users\Yusuf\Desktop\Roblox Player.lnk",
    "roblox":             r"C:\Users\Yusuf\Desktop\Roblox Player.lnk",
    "роблокс студио":     r"C:\Users\Yusuf\Desktop\Roblox Studio.lnk",
    "roblox studio":      r"C:\Users\Yusuf\Desktop\Roblox Studio.lnk",
    "стим":               r"C:\Users\Yusuf\Desktop\Steam.lnk",
    "steam":              r"C:\Users\Yusuf\Desktop\Steam.lnk",
    "вр":                 r"C:\Users\Yusuf\Desktop\SteamVR.url",
    "steam vr":           r"C:\Users\Yusuf\Desktop\SteamVR.url",
    "майнкрафт":          r"C:\Users\Yusuf\Desktop\Minecraft.exe",
    "minecraft":          r"C:\Users\Yusuf\Desktop\Minecraft.exe",
    "маенкрафт":          r"C:\Users\Yusuf\Desktop\Minecraft.exe",
    "супер сус":          r"C:\Users\Yusuf\Desktop\Super Sus.url",
    "super sus":          r"C:\Users\Yusuf\Desktop\Super Sus.url",
    "поппи плейтайм":     r"C:\Users\Yusuf\Desktop\Poppy Playtime.url",
    "poppy":              r"C:\Users\Yusuf\Desktop\Poppy Playtime.url",
    "poppy playtime":     r"C:\Users\Yusuf\Desktop\Poppy Playtime.url",
    "привет сосед":       r"C:\Users\Yusuf\Desktop\Hello Neighbor 2 Demo.url",
    "hello neighbor":     r"C:\Users\Yusuf\Desktop\Hello Neighbor 2 Demo.url",
    "hello neighbor 2":   r"C:\Users\Yusuf\Desktop\Hello Neighbor 2 Demo.url",
    "инры":               r"C:\Users\Yusuf\Desktop\Инры.lnk",
    "игры":               r"C:\Users\Yusuf\Desktop\Инры.lnk",
    "эмулятор андроид":   r"C:\Users\Yusuf\Desktop\LDPlayer 9.lnk",
    "лдплеер":            r"C:\Users\Yusuf\Desktop\LDPlayer 9.lnk",
    "ldplayer":           r"C:\Users\Yusuf\Desktop\LDPlayer 9.lnk",

    # ============ ЭМУЛЯЦИЯ / VR ============
    "пико":               r"C:\Users\Yusuf\Desktop\Pico Link.url",
    "pico":               r"C:\Users\Yusuf\Desktop\Pico Link.url",
    "пико линк":          r"C:\Users\Yusuf\Desktop\Pico Link.url",

    # ============ СВЯЗЬ ============
    "телеграм":           r"C:\Users\Yusuf\Desktop\Telegram.lnk",
    "telegram":           r"C:\Users\Yusuf\Desktop\Telegram.lnk",
    "телег":              r"C:\Users\Yusuf\Desktop\Telegram.lnk",
    "телефон":            r"C:\Users\Yusuf\Desktop\Связь с телефоном.lnk",
    "связь с телефоном":  r"C:\Users\Yusuf\Desktop\Связь с телефоном.lnk",

    # ============ УЧЁБА ============
    "мэш":                r"C:\Users\Yusuf\Desktop\МЭШ.url",
    "меш":                r"C:\Users\Yusuf\Desktop\МЭШ.url",
    "московская школа":   r"C:\Users\Yusuf\Desktop\МЭШ.url",
    "школа":              r"C:\Users\Yusuf\Desktop\Школа.lnk",
    "алгебра":            r"C:\Users\Yusuf\Desktop\Агебра.pdf",
    "английский":         r"C:\Users\Yusuf\Desktop\Английский.pdf",
    "русский":            r"C:\Users\Yusuf\Desktop\Русский.pdf",
    "экзамен":            r"C:\Users\Yusuf\Desktop\Eyes on the Exam Demo.url",
    "eyes on the exam":   r"C:\Users\Yusuf\Desktop\Eyes on the Exam Demo.url",

    # ============ ХОББИ ============
    "дроны":              r"C:\Users\Yusuf\Desktop\Дроны програмирование.exe",
    "программирование дронов": r"C:\Users\Yusuf\Desktop\Дроны програмирование.exe",
    "программирование":   r"C:\Users\Yusuf\Desktop\Программивоние.lnk",
    "бинды":              r"C:\Users\Yusuf\Desktop\Бинды элемент крафт.lnk",
    "элемент крафт":      r"C:\Users\Yusuf\Desktop\Бинды элемент крафт.lnk",
    "кьюар код":          r"C:\Users\Yusuf\Desktop\QR_Code.exe",
    "qr код":             r"C:\Users\Yusuf\Desktop\QR_Code.exe",
    "генератор кьюар":    r"C:\Users\Yusuf\Desktop\QR_Code.exe",
    "базовые приложения": r"C:\Users\Yusuf\Desktop\Базавые приожухи.lnk",
    "приложения":         r"C:\Users\Yusuf\Desktop\Базавые приожухи.lnk",

    # ============ КЕША ============
    "кеша ассистент":     r"C:\Users\Yusuf\Desktop\KeshaAssistant.exe",
    "ассистент":          r"C:\Users\Yusuf\Desktop\KeshaAssistant.exe",
    "kesha":              r"C:\Users\Yusuf\Desktop\KeshaAssistant.exe",
}

# Встроенные программы Windows (их нет ни на рабочем столе, ни в списке AppOpener)
BUILTIN_APPS = {
    "калькулятор": "calc.exe", "calculator": "calc.exe",
    "диспетчер задач": "taskmgr.exe", "панель управления": "control.exe",
    "ножницы": "snippingtool.exe", "экранная клавиатура": "osk.exe",
    "экранную клавиатуру": "osk.exe", "лупа": "magnify.exe", "лупу": "magnify.exe",
}

# ============================================================
#  ПУТИ К ВСПОМОГАТЕЛЬНЫМ ФАЙЛАМ
# ============================================================
TIMER_PATH = str(MEDIA_DIR / "timer.py")
ICON_PATH  = str(MEDIA_DIR / "Kesha_icoc.jpeg")
ICON_PNG   = str(MEDIA_DIR / "Kesha_icoc.png")
LOGO_PATH  = str(MEDIA_DIR / "Kesha_logo.png")
ALARM_SOUND = str(MEDIA_DIR / "basic-alarm-ringtone.mp3")

# ============================================================
#  WAKE-WORDS
# ============================================================
WAKE_WORDS = ["кеша", "кеш", "гоша", "чебурек", "кэш"]
# Как GigaAM иногда слышит «Кеша». Считаются словом-активатором, только если стоят
# в начале фразы (иначе «каша на завтрак» будила бы Кешу).
WAKE_ALIASES = ["каша", "кеши", "кеше", "кешу", "геша", "киша", "беша", "кэша", "кеща", "тееша", "хеша", "кьеша"]

# ============================================================
#  ФРАЗЫ
# ============================================================
GREETINGS = [
    "Приветствую! Чем могу быть полезен?",
    "Здравствуйте! Готов к работе.",
    "Слушаю вас.",
    "Весь во внимании.",
    "Да, я здесь.",
    "Привет! Что нужно сделать?",
    "Здравствуй. Говори, что надо."
]

THANKS_RESPONSES = [
    "Рад стараться!",
    "Всегда пожалуйста!",
    "Это моя работа.",
    "Обращайтесь.",
    "Не за что.",
    "Для вас — что угодно."
]

OK_RESPONSES = [
    "Готово.",
    "Сделано.",
    "Исполнено.",
    "Уже сделал.",
    "Без проблем.",
    "Так точно."
]

SEARCH_RESPONSES = [
    "Вот что удалось найти.",
    "Результаты поиска перед вами.",
    "Ищу информацию.",
    "Открываю результаты.",
    "Секунду, ищу."
]

# ============================================================
#  ТОКЕНЫ И ПАРОЛИ (значения лежат в .env)
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
WEB_PASSWORD   = os.getenv("WEB_PASSWORD", "")


def _id_set(name):
    return {x.strip() for x in os.getenv(name, "").split(",") if x.strip()}


# Кому можно управлять ПК. Пусто = никому (доступ закрыт).
TELEGRAM_ALLOWED_IDS = _id_set("TELEGRAM_ALLOWED_IDS")   # числовые user_id, через запятую
ALICE_ALLOWED_IDS    = _id_set("ALICE_ALLOWED_IDS")      # user_id / application_id из лога навыка

# ============================================================
#  НАСТРОЙКИ ГОЛОСА
# ============================================================
# Приложение Яндекс Музыки: «включи музыку» открывает его, а не сайт (можно переопределить в .env)
YANDEX_MUSIC_EXE = os.getenv("YANDEX_MUSIC_EXE", r"C:\Users\Yusuf\AppData\Local\Programs\YandexMusic\Яндекс Музыка.exe")
MIC_ACTIVE_WINDOW = 10
# услышала «Кеша» — остальные приложения (музыка, видео) тише до этой доли, пока слушает и
# отвечает; как у Алисы, чтобы фон не попадал в запись. 0 — не приглушать
DUCK_LEVEL = 0.2
MIC_TIMEOUT = 5
# Тише этого (dBFS) — не речь, а шум комнаты: webrtcvad срабатывал на −70 dB,
# и GigaAM впустую распознавал тишину. Речь в логах — от −62 dB и громче.
MIN_SPEECH_DB = float(os.getenv("MIN_SPEECH_DB", "-64"))
TTS_LANG = "ru"
TTS_SLOW = False

# ============================================================
#  НАСТРОЙКИ СЕТИ
# ============================================================
WEB_HOST   = "0.0.0.0"
WEB_PORT   = 8000
ALICE_HOST = "127.0.0.1"
ALICE_PORT = 5656

# ============================================================
#  НАСТРОЙКИ UI
# ============================================================
DESKTOP_WIDTH  = 1280
DESKTOP_HEIGHT = 720
DESKTOP_TITLE  = "Голосовой помощник Кеша"

# ============================================================
#  ПОГОДА
# ============================================================
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_CITY    = "Сосенки"            # дом: Сосенки (Коммунарка)
WEATHER_COORDS  = (55.583, 37.454)     # по координатам — OpenWeather не знает Сосенки по названию

# ============================================================
#  ПОНИМАНИЕ ФРАЗ (волна 2)
# ============================================================
FUZZY_THRESHOLD = 0.84        # порог похожести (0..1) для нечёткого поиска
FUZZY_THRESHOLD_LONG = 0.80   # порог для длинных паттернов (>= 12 символов)
FUZZY_MIN_LEN = 5             # короче — паттерн не участвует в нечётком поиске

SESSION_STEPS = 3             # сколько последних реплик помним
SESSION_TTL = 300             # через сколько секунд контекст «протухает»

AI_CACHE_FILE = DATA_DIR / "ai_cache.json"
AI_CACHE_TTL  = 24 * 3600     # сколько живёт ответ GigaChat в кэше, сек
AI_CACHE_MAX  = 500           # максимум записей в кэше
AI_COMMANDS_MAX_WORDS = 8     # длиннее — это вопрос, список команд GigaChat не шлём
AI_MAX_WORDS = 10             # ответ GigaChat голосом — не длиннее стольких слов
AI_FIX_COMMANDS = True        # без «Кеша» в окне команд: GigaChat исправляет фразу в команду (не отвечает)
AI_FIX_MAX_WORDS = 5          # длиннее — фон, не спрашиваем

UNKNOWN_LOG_FILE = LOGS_DIR / "kesha.log"

# ============================================================
#  УДОБСТВО (волна 3)
# ============================================================
HOTKEY = "ctrl+space"          # слушать без слова «Кеша»; "" — отключить

# Распознавание команд: "aqua" (Avalon API, нужен AQUA_API_KEY) | "local" (GigaAM офлайн; "vosk" — то же).
# При сбое Aqua Кеша сама переходит на локальный. Слово-активатор всегда ищется локально.
STT_ENGINE = "aqua"

# Защита. Чёрный список: что Кеша не открывает никогда (по любому каналу).
SECURITY_BLOCKED_APPS = [
    "cmd", "cmd.exe", "командная строка", "командную строку", "командной строки",
    "powershell", "пауэршелл", "повершелл", "терминал", "terminal", "консоль",
    "regedit", "реестр", "редактор реестра", "diskpart", "bcdedit", "gpedit",
    "msconfig", "mmc", "services.msc", "управление дисками", "format",
]
# Белый список: если не пуст — открываются ТОЛЬКО эти приложения.
SECURITY_ALLOWED_APPS = []
# «Выполнить» и меню администратора дают запустить что угодно.
SECURITY_BLOCKED_KEYS = ["win+r", "win+x", "ctrl+alt+delete", "ctrl+alt+del"]
# Регулярки текста, который Кеша не напечатает (команды удаления/форматирования).
SECURITY_BLOCKED_TEXT = [
    r"\brmdir\b", r"\brd\s+/s\b", r"\bdel\s+(/[a-z]\s+)*[a-z]:\\", r"\bformat\s+[a-z]:?(?!\w)",
    r"\breg\s+delete\b", r"\brm\s+-rf?\b", r"\bremove-item\b", r"\bdiskpart\b",
    r"\bbcdedit\b", r"\bcipher\s+/w\b", r"\bvssadmin\b", r"\btakeown\b",
    r"system32", r"\bshutdown\s+/",
]

SHOUT_DB = -14.0               # громче этого (dBFS) — Кеша считает, что на неё кричат
SHOUT_MARGIN_DB = 9.0          # ...и на столько громче обычной речи пользователя

# ============================================================
#  ФИЧИ (волна 4)
# ============================================================
REMINDERS_FILE = DATA_DIR / "reminders.json"
NOTES_FILE     = DATA_DIR / "notes.json"
CALENDAR_FILE  = DATA_DIR / "calendar.json"
STATS_DB       = DATA_DIR / "stats.db"
TELEGRAM_USERS_FILE = DATA_DIR / "telegram_users.json"
ALARM_MAX_SEC  = 120           # будильник звонит максимум столько секунд

# Календарь: ссылки ICS (Google — «Закрытый адрес в формате iCal»,
# Яндекс — «Экспорт» -> ссылка .ics) через запятую.
CALENDAR_ICS_URLS = [u.strip() for u in os.getenv("CALENDAR_ICS_URLS", "").split(",") if u.strip()]
# Запись событий в Яндекс Календарь по CalDAV (пароль приложения Яндекса).
CALDAV_URL      = os.getenv("CALDAV_URL", "")       # https://caldav.yandex.ru/calendars/<логин>/events-default/
CALDAV_USER     = os.getenv("CALDAV_USER", "")
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD", "")
TIMEZONE        = "Europe/Moscow"

# Контакты для «напиши маме в телеграм»: имя:chat_id через запятую.
# Человек должен хотя бы раз написать боту (иначе Telegram не даст отправить).
TELEGRAM_CONTACTS = {
    k.strip().lower(): v.strip()
    for k, v in (pair.split(":", 1) for pair in os.getenv("TELEGRAM_CONTACTS", "").split(",") if ":" in pair)
}

# ============================================================
#  ГОЛОС (волна 5)
# ============================================================
# модель лежит в models/ (раньше искалась в корне — офлайн-голос молча не грузился)
SILERO_MODEL_PATH = next((p for p in (BASE_DIR / "models" / "silero_v5_6_ru.pt", BASE_DIR / "silero_v5_6_ru.pt")
                          if p.exists()), BASE_DIR / "models" / "silero_v5_6_ru.pt")
SILERO_SPEAKERS = {"female": "xenia", "male": "eugene", "robot": "eugene"}
SILERO_SAMPLE_RATE = 48000

# ============================================================
#  ПРОЧЕЕ
# ============================================================
DEBUG = True

# ============================================================
#  РОБОТ (Yahboom Raspbot V2 на Raspberry Pi 5)
# ============================================================
ROBOT_HOSTS = ["yahboom", "192.168.10.112", "192.168.1.56"]   # имя Pi, потом IP в разных сетях
ROBOT_PORT = 8180                        # robot-web.service (robot_web_final.py), /api/move без токена
ROBOT_URL = f"http://{ROBOT_HOSTS[0]}:{ROBOT_PORT}"
ROBOT_SSH = f"pi@{ROBOT_HOSTS[0]}"       # ssh по ключу, для Клода
ROBOT_SPEED = 150                        # 0–255
ROBOT_MOVE_SEC = 1.0                     # сколько едет по умолчанию, потом стоп
