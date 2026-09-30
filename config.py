"""
Все настройки проекта Кеша.
Все пути, токены, фразы и константы.
"""

import os
from pathlib import Path

# ============================================================
#  БАЗОВЫЕ ПУТИ
# ============================================================
BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / "Media"
UPLOAD_DIR = BASE_DIR / "uploads"
LOGS_DIR = BASE_DIR / "logs"

UPLOAD_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

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
#  ТОКЕНЫ И ПАРОЛИ
# ============================================================
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
WEB_PASSWORD   = "CHANGE_ME"

# ============================================================
#  НАСТРОЙКИ ГОЛОСА
# ============================================================
MIC_ACTIVE_WINDOW = 10
MIC_TIMEOUT = 5
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
WEATHER_API_KEY = "YOUR_OPENWEATHER_KEY"
WEATHER_CITY    = "Москва"

# ============================================================
#  ПРОЧЕЕ
# ============================================================
DEBUG = True