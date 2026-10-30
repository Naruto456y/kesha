"""Волна 6: утилиты (калькулятор, случайность, «повтори», секундомер, дни до даты…)."""
from datetime import date

import pytest

import core
from core import handle_command
from features import utilities as u


@pytest.mark.parametrize("phrase, value", [
    ("сколько будет 2 плюс 2", 4),
    ("сколько будет двадцать пять умножить на четыре", 100),
    ("посчитай 100 разделить на 8", 12.5),
    ("сколько будет 7 минус 10", -3),
    ("корень из 144", 12),
    ("сколько будет 5 в квадрате", 25),
    ("15 процентов от 2000", 300),
    ("посчитай 2 плюс 2 умножить на 2", 6),
    ("вычисли 3,5 плюс 1,5", 5),
])
def test_calculate(phrase, value):
    assert u.calculate(phrase) == pytest.approx(value)


@pytest.mark.parametrize("phrase", [
    "сколько будет 100 долларов в рублях", "плюсы и минусы ноутбука", "открой калькулятор",
    "сколько будет", "посчитай калории", "сколько будет 2 в степени 1000",
])
def test_calculate_rejects_non_math(phrase):
    assert u.calculate(phrase) is None


def test_calc_command_and_zero():
    assert handle_command("сколько будет 6 умножить на 7", ai=False) == "Получается 42."
    assert "ноль" in handle_command("посчитай 5 разделить на 0", ai=False)
    assert handle_command("сколько будет 1 разделить на 3", ai=False) == "Получается 0,333333."


def test_calc_leaves_money_to_rates(monkeypatch):
    from features import rates
    monkeypatch.setattr(rates, "cbr_rate", lambda code: (90.0, 0.0))
    assert handle_command("сколько будет 100 долларов в рублях", ai=False) == "100 доллар — это 9 000 ₽"


def test_random_commands():
    assert handle_command("подбрось монетку", ai=False) in ("Орёл!", "Решка!")
    r = handle_command("кинь кубик", ai=False)
    assert r.startswith("Выпало ") and 1 <= int(r.split()[1].rstrip(".")) <= 6
    for _ in range(20):
        n = int(handle_command("случайное число от 5 до 7", ai=False).rstrip("."))
        assert 5 <= n <= 7


def test_repeat_last():
    u._last.clear(); u._last_cmd.clear()
    assert handle_command("повтори", source="telegram", ai=False) == "Пока нечего повторять."
    assert handle_command("сколько будет 3 плюс 4", source="telegram", ai=False) == "Получается 7."
    assert handle_command("повтори", source="telegram", ai=False) == "Получается 7."
    assert handle_command("повтори", source="website", ai=False) == "Пока нечего повторять."


def test_skills_and_joke():
    assert "музыку" in handle_command("что ты умеешь", ai=False)
    assert "команд" in handle_command("список команд", ai=False)
    assert handle_command("расскажи анекдот", ai=False) in u.JOKES


@pytest.mark.parametrize("phrase, today, days", [
    ("сколько дней до нового года", date(2026, 12, 30), 2),
    ("сколько осталось до лета", date(2026, 5, 31), 1),
    ("сколько дней до первого сентября", date(2026, 8, 30), 2),
    ("сколько дней до 25 декабря", date(2026, 12, 26), 364),
    ("сколько дней до двадцать пятого мая", date(2026, 5, 20), 5),
    ("сколько дней до 8 марта", date(2026, 3, 8), 0),
])
def test_days_until(phrase, today, days):
    assert u.days_until(phrase, today)[0] == days


def test_days_left_reply():
    assert handle_command("сколько дней до нового года", ai=False).startswith("До Нового года ")
    assert u.days_until("сколько дней до 31 февраля") is None


def test_stopwatch(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(u.time, "time", lambda: clock[0])
    u._sw.update(start=None, acc=0.0)
    assert "не запущен" in handle_command("сколько на секундомере", ai=False)
    assert "пошёл" in handle_command("запусти секундомер", ai=False)
    clock[0] += 12.34
    assert handle_command("сколько на секундомере", ai=False) == "Прошло 12,3 секунды."
    clock[0] += 120
    assert handle_command("стоп секундомер", ai=False) == "Стоп! Прошло 2 минуты 12 секунд."
    assert "не был запущен" in handle_command("останови секундомер", ai=False)


def test_stopwatch_does_not_steal_timer_or_music(monkeypatch):
    names = []
    monkeypatch.setattr(core, "_command_hooks", [lambda s, n, t, r: names.append(n)])
    import commands, keyboard
    monkeypatch.setattr(keyboard, "send", lambda *a, **k: None)
    from features import reminders
    monkeypatch.setattr(reminders, "add_timer", lambda text: "таймер")
    handle_command("засеки 5 минут", ai=False)
    handle_command("стоп", ai=False)
    assert names == ["set_timer", "music_pause"]


def test_system_and_internet(monkeypatch):
    assert handle_command("нагрузка компьютера", ai=False).startswith("Процессор загружен на ")
    monkeypatch.setattr(u, "internet_ok", lambda timeout=2.0: 23.4)
    assert handle_command("есть ли интернет", ai=False) == "Интернет есть, отклик 23 миллисекунд."
    monkeypatch.setattr(u, "internet_ok", lambda timeout=2.0: None)
    assert handle_command("проверь интернет", ai=False).startswith("Интернета нет")


def test_mute_and_clipboard(monkeypatch):
    calls = []
    monkeypatch.setattr(u, "set_mute", lambda on: calls.append(on) or True)
    assert handle_command("выключи звук", ai=False) == "Звук выключен."
    assert handle_command("включи звук", ai=False) == "Звук включён."
    assert calls == [True, False]
    import pyperclip
    monkeypatch.setattr(pyperclip, "paste", lambda: "  привет из буфера ")
    assert handle_command("прочитай буфер обмена", ai=False) == "привет из буфера"


# ---------- поиск программ по ярлыкам ----------
FAKE_INDEX = {"obsidian": "O.lnk", "telegram": "T.lnk", "dota 2": "D.url", "blender 4.2": "B.lnk",
              "google chrome": "C.lnk", "git bash": "G.lnk", "paint": "P.lnk"}


@pytest.mark.parametrize("query, name", [
    ("обсидиан", "obsidian"), ("psidion", "obsidian"), ("bsidin", "obsidian"), ("epident", "obsidian"),
    ("телеграм", "telegram"), ("доту", "dota 2"), ("блендер", "blender 4.2"), ("blender", "blender 4.2"),
    ("гит баш", "git bash"), ("пожалуйста paint", "paint"), ("obsidain", "obsidian"),
])
def test_app_index_find(query, name):
    import app_index
    assert app_index.find(query, FAKE_INDEX)[0] == name


@pytest.mark.parametrize("query", ["штуку с кубиками", "кубики", "майнкрафт", "", "что-нибудь"])
def test_app_index_no_guessing(query):
    import app_index
    assert app_index.find(query, FAKE_INDEX) is None


def test_open_app_uses_shortcuts(monkeypatch):
    import commands, app_index
    started = []
    monkeypatch.setattr(app_index, "shortcuts", lambda refresh=False: FAKE_INDEX)
    monkeypatch.setattr(commands.os, "startfile", lambda p: started.append(p))
    assert handle_command("открой psidion", ai=False) == "Открываю obsidian"
    assert handle_command("bsidin открой", ai=False) == "Открываю obsidian"
    assert started == ["O.lnk", "O.lnk"]


# ---------- VAD: тишина −70 dB не превращается в «(пусто)» ----------
def _vad_with(monkeypatch, frames):
    import numpy as np
    from voice import vad_recorder as vr

    class FakeStream:
        def __init__(self, **k):
            self.frames = list(frames)
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self, n):
            f = self.frames.pop(0) if self.frames else np.zeros(n, dtype=np.int16)
            return f.tobytes(), False

    class AlwaysSpeech:          # webrtcvad, который «слышит речь» даже в тишине
        def is_speech(self, frame, rate):
            return True

    monkeypatch.setattr(vr.sd, "RawInputStream", FakeStream)
    rec = vr.VADRecorder(min_db=-64)
    rec.vad = AlwaysSpeech()
    return rec


def _frames(db, seconds):
    import numpy as np
    from voice.vad_recorder import FRAME_SAMPLES
    amp = 32768 * 10 ** (db / 20) * np.sqrt(2)
    t = np.arange(FRAME_SAMPLES) / 16000
    one = (amp * np.sin(2 * np.pi * 300 * t)).astype(np.int16)
    return [one] * int(seconds * 1000 / 30)


def test_vad_ignores_room_noise(monkeypatch):
    rec = _vad_with(monkeypatch, _frames(-72, 2))
    assert rec.record(max_wait=1.0) == b""
    assert rec.last_info["stopped_by"] in ("no_speech", "quiet")


def test_vad_keeps_real_speech(monkeypatch):
    rec = _vad_with(monkeypatch, _frames(-72, 0.5) + _frames(-40, 0.6) + _frames(-90, 1.5))
    audio = rec.record(max_wait=3.0)
    assert rec.last_info["stopped_by"] == "silence"
    assert 0.5 <= len(audio) / 32000 <= 1.2


# ---------- фразы из сухого прогона: раньше уходили не туда ----------
def _names(monkeypatch):
    names = []
    monkeypatch.setattr(core, "_command_hooks", [lambda s, n, t, r: names.append(n)])
    return names


@pytest.mark.parametrize("phrase, expected", [
    ("переведи привет на английский", "привет"),
    ("как будет собака по-английски", "собака"),
    ("переведи hello", "hello"),
    ("переведи good morning на русский", "good morning"),
])
def test_translate_free(monkeypatch, phrase, expected):
    import commands
    asked = []
    monkeypatch.setattr(commands, "GIGACHAT_AVAILABLE", True)
    monkeypatch.setattr(commands, "_gig", type("G", (), {"chat": lambda self, q: asked.append(q) or "ok"})())
    names = _names(monkeypatch)
    assert handle_command(phrase, ai=False) == "ok"
    assert names == ["translate_free"]
    assert asked[0].endswith(f": {expected}. Без объяснений.")
    assert ("на русский" in asked[0]) == bool(__import__("re").search("[a-z]", expected))


def test_translate_free_ignores_non_translation(monkeypatch):
    import commands
    monkeypatch.setattr(commands, "_fetch_forecast", lambda city: None)
    names = _names(monkeypatch)
    handle_command("как будет погода завтра", ai=False)
    assert names == ["weather_forecast"]


@pytest.mark.parametrize("phrase, name", [
    ("сколько щас времени", "get_time"), ("сверни все окна", "show_desktop"),
    ("покажи рабочий стол", "show_desktop"), ("открой загрузки", "open_folder"),
    ("ты кто", "about_me"), ("кеша ты тут", "are_you_here"), ("что делаешь", "what_doing"),
    ("какие у меня будильники", "list_reminders"), ("до завтра", "goodbye"),
    ("режим не беспокоить", "silent_mode"), ("нужен ли зонт", "get_weather_cmd"),
    ("что надеть в школу", "get_weather_cmd"),
])
def test_new_patterns_route(monkeypatch, phrase, name):
    import commands, keyboard, settings
    monkeypatch.setattr(keyboard, "send", lambda *a, **k: None)
    monkeypatch.setattr(commands.os, "startfile", lambda p: None)
    monkeypatch.setattr(commands, "_resolve_weather", lambda text, fetch: (None, "x"))
    names = _names(monkeypatch)
    handle_command(phrase, ai=False)
    assert names == [name]
    settings.set("silent", False)


def test_weather_advice_and_school_is_not_a_city(monkeypatch):
    import commands
    data = {"main": {"temp": 3}, "weather": [{"description": "небольшой дождь"}], "name": "Москва"}
    seen = []
    monkeypatch.setattr(commands, "_fetch_weather", lambda c: seen.append(c) or data)
    r = handle_command("нужен ли зонт", ai=False)
    assert r.endswith("Зонт лучше взять.")
    r = handle_command("что надеть в школу", ai=False)
    assert "тёплая куртка" in r and "школ" not in seen[-1]


def test_note_strips_word_note_and_date_weekday():
    assert handle_command("запиши заметку купить хлеб", ai=False) == "Записал: купить хлеб"
    r = handle_command("какой сегодня день недели", ai=False)
    assert r.startswith("Сегодня ") and r.rstrip(".").split()[-1] in __import__("commands")._WEEKDAYS_RU


def test_minecraft_video_searches_youtube(monkeypatch):
    import commands
    monkeypatch.setattr(commands, "search_youtube", lambda text: "видео: " + text)
    started = []
    monkeypatch.setattr(commands.os, "startfile", lambda p: started.append(p))
    r = handle_command("включи видео про майнкрафт", ai=False)
    assert r.startswith("видео: ") and "майнкрафт" in r and not started


def test_goodnight():
    assert handle_command("спокойной ночи", ai=False) == "Спокойной ночи! Сладких снов."


def test_telegram_conflict_logged_once(caplog):
    import asyncio
    from telegram.error import Conflict
    from telegram_bot import bot
    bot._conflict_warned = False
    ctx = type("C", (), {"error": Conflict("terminated by other getUpdates request")})()
    with caplog.at_level("ERROR"):
        for _ in range(3):
            asyncio.run(bot.on_error(None, ctx))
    hits = [r for r in caplog.records if "Conflict" in r.getMessage()]
    assert len(hits) == 1 and "@BotFather" in hits[0].getMessage()


# ---------- день рождения и сводка ----------
def test_birthday_flow():
    import settings
    assert "не знаю" in handle_command("сколько дней до дня рождения", ai=False).lower()
    r = handle_command("мой день рождения двадцать пятого декабря", ai=False)
    assert r.startswith("Запомнил: 25 декабря.")
    assert settings.get("birthday") == [12, 25]
    assert u.days_until("сколько дней до дня рождения", date(2026, 12, 20))[0] == 5
    assert handle_command("когда мой день рождения", ai=False) == "Твой день рождения 25 декабря."
    assert u.parse_day_month("31 февраля") is None and u.parse_day_month("29 февраля") == (2, 29)


def test_briefing(monkeypatch):
    import commands
    from features import reminders
    monkeypatch.setattr(commands, "_resolve_weather",
                        lambda text, fetch: ({"main": {"temp": 7}, "weather": [{"description": "ясно"}], "name": "Москва"}, "x"))
    reminders.add_timer("таймер на 5 минут")
    r = handle_command("утренняя сводка", ai=False)
    assert r.startswith("Сегодня ") and "Погода: Москва: 7°C, ясно" in r and "Напоминания:" in r


# ---------- «пока» закрывает Кешу, камера без Win+цифр ----------
@pytest.fixture
def exits(monkeypatch):
    import lifecycle
    calls = []
    monkeypatch.setattr(lifecycle, "request_exit", lambda *a, **k: calls.append(1) or True)
    return calls


@pytest.mark.parametrize("phrase", ["пока", "кеша пока", "хеша пока", "ну всё пока", "до свидания",
                                    "выключись", "попака", "закройся"])
def test_bye_quits(exits, phrase):
    r = handle_command(phrase, source="voice", ai=False)
    assert r == "До свидания! Выключаюсь." and exits == [1]


@pytest.mark.parametrize("phrase", [
    "пока я был в бассейне у меня болели ноги", "пока что не надо", "я пока не решил что смотреть"])
def test_pokа_inside_speech_does_not_quit(exits, phrase):
    handle_command(phrase, source="voice", ai=False)
    assert exits == []


def test_bye_from_telegram_does_not_quit(exits):
    assert "удалённо" in handle_command("пока", source="telegram", ai=False)
    assert exits == []


def test_soft_goodbyes_do_not_quit(exits):
    assert handle_command("до завтра", source="voice", ai=False) == "До завтра!"
    assert handle_command("увидимся", source="voice", ai=False)
    assert exits == []


def test_lifecycle_runs_hooks_once(monkeypatch):
    import lifecycle
    done = []
    monkeypatch.setattr(lifecycle, "_requested", False)
    monkeypatch.setattr(lifecycle, "_hooks", [lambda: done.append("cleanup")])
    monkeypatch.setattr(lifecycle, "_speaking", lambda: False)
    monkeypatch.setattr(lifecycle.os, "_exit", lambda code: done.append(f"exit{code}"))
    monkeypatch.setattr(lifecycle.time, "sleep", lambda s: None)
    assert lifecycle.request_exit(delay=0) is True and lifecycle.request_exit() is False
    for t in __import__("threading").enumerate():
        if t.name == "exit":
            t.join(2)
    assert done == ["cleanup", "exit0"]


def test_camera_uses_app_uri_not_hotkeys(monkeypatch):
    import commands, keyboard
    started, keys = [], []
    monkeypatch.setattr(commands.os, "startfile", lambda p: started.append(p))
    monkeypatch.setattr(keyboard, "send", lambda k: keys.append(k))
    assert handle_command("открой камеру", ai=False) == "Открываю камеру"
    assert started == ["microsoft.windows.camera:"] and keys == []


def test_camera_fallback_and_failure(monkeypatch):
    import commands
    def boom(p):
        raise OSError("нет протокола")
    monkeypatch.setattr(commands.os, "startfile", boom)
    opened = []
    monkeypatch.setattr(commands.AppOpener, "open", lambda name, **k: opened.append(name))
    assert handle_command("включи камеру", ai=False) == "Открываю камеру" and opened == ["camera"]
    monkeypatch.setattr(commands.AppOpener, "open", lambda name, **k: (_ for _ in ()).throw(RuntimeError()))
    assert "Не нашёл" in handle_command("включи камеру", ai=False)


def test_selfie_launches_camera_then_space(monkeypatch):
    import commands, keyboard
    started, keys = [], []
    monkeypatch.setattr(commands.os, "startfile", lambda p: started.append(p))
    monkeypatch.setattr(keyboard, "send", lambda k: keys.append(k))
    monkeypatch.setattr(commands.time, "sleep", lambda s: None)
    class Now:
        def __init__(self, delay, fn): self.fn = fn
        def start(self): self.fn()
    monkeypatch.setattr(commands.threading, "Timer", Now)
    assert handle_command("селфи", ai=False) == "Улыбнитесь!"
    assert started == ["microsoft.windows.camera:"] and keys == ["space"]


def test_wifi_and_wake_alias(monkeypatch):
    import commands
    started = []
    monkeypatch.setattr(commands.os, "startfile", lambda p: started.append(p))
    assert "Wi-Fi" in handle_command("wi-fi", ai=False) and started == ["ms-settings:network-wifi"]
    from voice.listener import _has_wake, _clean
    assert _has_wake("хеша пока") and _clean("хеша пока") == "пока"


# ---------- «повтори» повторяет команду, а не ответ ----------
def test_repeat_reruns_command_not_answer(monkeypatch):
    u._last.clear(); u._last_cmd.clear()
    seq = iter(["Орёл!", "Решка!", "Орёл!"])
    monkeypatch.setattr(u.random, "choice", lambda items: next(seq) if "Орёл!" in items else items[0])
    assert handle_command("подбрось монетку", source="voice", ai=False) == "Орёл!"
    assert handle_command("повтори", source="voice", ai=False) == "Решка!"      # заново бросила, а не «Орёл!»
    assert handle_command("ещё раз", source="voice", ai=False) == "Орёл!"       # «повтори» не затирает исходную команду


def test_repeat_answer_still_available():
    u._last.clear(); u._last_cmd.clear()
    r = handle_command("сколько будет 2 плюс 2", source="voice", ai=False)
    assert handle_command("что ты сказала", source="voice", ai=False) == r == "Получается 4."


def test_repeat_refuses_risky_and_skips_ai(monkeypatch):
    import commands
    u._last.clear(); u._last_cmd.clear()
    monkeypatch.setattr(commands.os, "system", lambda *a: 0)
    handle_command("выключи компьютер", source="voice", ai=False)
    assert "опасная" in handle_command("повтори", source="voice", ai=False)
    u._last_cmd.clear()
    monkeypatch.setattr(core, "ai_ask", lambda *a, **k: "ответ GigaChat")
    handle_command("расскажи про динозавров", source="voice")
    assert handle_command("повтори", source="voice", ai=False) == "Пока нечего повторять."


# ---------- Яндекс Музыка: жёлтая кнопка через ScreenReader ----------
def test_yamusic_templates_exist():
    from features import yamusic
    assert [p.stem for p in yamusic.TEMPLATES] == ["play_75", "play_100", "play_125", "play_150", "play_200"]


def test_yamusic_clicks_found_button(monkeypatch):
    import help_manager, pyautogui
    from features import yamusic
    clicks, tried = [], []
    def fake_find(path, confidence=0.8, region=None):
        tried.append(path.rsplit("_", 1)[1])
        return (640, 360) if path.endswith("play_125.png") else None
    monkeypatch.setattr(help_manager.ScreenReader, "find_image", staticmethod(fake_find))
    monkeypatch.setattr(pyautogui, "click", lambda x, y: clicks.append((x, y)))
    monkeypatch.setattr(yamusic.time, "sleep", lambda s: None)
    assert yamusic.click_play(timeout=5) is True
    assert clicks == [(640, 360)] and tried == ["75.png", "100.png", "125.png"]


def test_yamusic_gives_up_when_music_already_playing(monkeypatch):
    import help_manager, pyautogui
    from features import yamusic
    clicks = []
    monkeypatch.setattr(help_manager.ScreenReader, "find_image", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(pyautogui, "click", lambda x, y: clicks.append(1))
    t = [0.0]
    monkeypatch.setattr(yamusic.time, "time", lambda: t[0])
    monkeypatch.setattr(yamusic.time, "sleep", lambda s: t.__setitem__(0, t[0] + 10))
    assert yamusic.click_play(timeout=25) is False and clicks == []


def test_play_music_opens_app_and_starts_button_search(monkeypatch):
    import commands
    from features import yamusic
    started, opened, searches = [], [], []
    monkeypatch.setattr(commands.os.path, "exists", lambda p: True)
    monkeypatch.setattr(commands.os, "startfile", lambda p: started.append(p))
    monkeypatch.setattr(commands.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(yamusic, "click_play_async", lambda **k: searches.append(1))
    assert handle_command("включи музыку", ai=False) == "Открываю Яндекс.Музыку"
    assert started == [commands.YANDEX_MUSIC_EXE] and commands.YANDEX_MUSIC_EXE.endswith("Яндекс Музыка.exe")
    assert opened == [] and searches == [1]


def test_play_music_falls_back_to_site_without_app(monkeypatch):
    import commands
    from features import yamusic
    opened = []
    monkeypatch.setattr(commands.os.path, "exists", lambda p: False)
    monkeypatch.setattr(commands.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(yamusic, "click_play_async", lambda **k: None)
    handle_command("включи музыку", ai=False)
    assert opened == ["https://music.yandex.ru/"]


def test_my_wave_uses_app_too(monkeypatch):
    import commands, keyboard
    from features import yamusic
    started = []
    monkeypatch.setattr(commands.os.path, "exists", lambda p: True)
    monkeypatch.setattr(commands.os, "startfile", lambda p: started.append(p))
    monkeypatch.setattr(yamusic, "click_play", lambda **k: True)
    monkeypatch.setattr(keyboard, "send", lambda k: pytest.fail("кнопку нашли — клавиша не нужна"))
    assert handle_command("включи мою волну", ai=False) == "Включаю мою волну"
    assert started == [commands.YANDEX_MUSIC_EXE]


# ---------- клавиши плеера: сайт в фокусе / музыка в фоне ----------
@pytest.mark.parametrize("title, phrase, key", [
    ("Яндекс Музыка — Главная - Google Chrome", "следующий трек", "n"),
    ("Яндекс Музыка — Главная - Google Chrome", "пауза", "k"),
    ("Яндекс Музыка — Главная - Google Chrome", "продолжи музыку", "k"),
    ("Яндекс Музыка — Главная - Google Chrome", "предыдущий трек", "p"),
    ("Visual Studio Code", "следующий трек", "next track"),
    ("Visual Studio Code", "пауза", "play/pause media"),
    ("Visual Studio Code", "продолжи музыку", "play/pause media"),
    ("Visual Studio Code", "предыдущий трек", "previous track"),
    ("Видео про котиков - YouTube", "пауза", "k"),
])
def test_music_keys_depend_on_focus(monkeypatch, title, phrase, key):
    import commands, keyboard
    keys = []
    from features import yamusic
    monkeypatch.setattr(commands, "_foreground_title", lambda: title.lower())
    monkeypatch.setattr(yamusic, "logo_visible", lambda: False)
    monkeypatch.setattr(commands, "_yandex_music_running", lambda: True)
    monkeypatch.setattr(keyboard, "send", lambda k: keys.append(k))
    handle_command(phrase, ai=False)
    assert keys == [key]


def test_music_starts_yandex_when_closed(monkeypatch):
    import commands, keyboard
    from features import yamusic
    started, keys = [], []
    monkeypatch.setattr(commands, "_foreground_title", lambda: "visual studio code")
    monkeypatch.setattr(yamusic, "logo_visible", lambda: False)
    monkeypatch.setattr(commands, "_yandex_music_running", lambda: False)
    monkeypatch.setattr(commands, "_open_yandex_music", lambda: started.append(1))
    monkeypatch.setattr(yamusic, "click_play_async", lambda: started.append(2))
    monkeypatch.setattr(keyboard, "send", lambda k: keys.append(k))
    assert handle_command("продолжи музыку", ai=False) == "Включаю Яндекс Музыку"
    assert started == [1, 2] and keys == []


def test_logo_on_screen_means_site_keys(monkeypatch):
    import commands, keyboard
    from features import yamusic
    keys = []
    monkeypatch.setattr(commands, "_foreground_title", lambda: "новая вкладка - яндекс браузер")
    monkeypatch.setattr(yamusic, "logo_visible", lambda: True)
    monkeypatch.setattr(keyboard, "send", lambda k: keys.append(k))
    handle_command("следующий трек", ai=False)
    handle_command("пауза", ai=False)
    assert keys == ["n", "k"]


def _scene(bg, *items):
    import numpy as np, cv2
    from PIL import Image
    im = Image.new("RGB", (1280, 720), bg)
    for img, pos in items:
        im.paste(img, pos)
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


@pytest.mark.parametrize("bg", [(255, 255, 255), (30, 20, 40), (120, 120, 130)])
@pytest.mark.parametrize("scale", [0.6, 0.75, 1.0, 1.3, 1.6, 2.0])
def test_logo_found_on_any_background_and_scale(bg, scale):
    from PIL import Image
    from features import yamusic
    logo = Image.open(yamusic.LOGO).convert("RGB")
    logo = logo.resize((round(logo.width * scale), round(logo.height * scale)), Image.LANCZOS)
    assert yamusic.logo_score(_scene(bg, (logo, (200, 100)))) >= yamusic.LOGO_SCORE


def test_play_button_is_not_mistaken_for_logo():
    from PIL import Image, ImageDraw
    from features import yamusic
    btn = Image.new("RGB", (90, 90), (30, 20, 40))
    d = ImageDraw.Draw(btn)
    d.ellipse((5, 5, 85, 85), fill=(255, 255, 0))
    d.polygon([(35, 25), (35, 65), (65, 45)], fill=(0, 0, 0))
    assert yamusic.logo_score(_scene((30, 20, 40), (btn, (300, 300)))) < yamusic.LOGO_SCORE
    assert yamusic.logo_score(_scene((255, 255, 255))) == 0.0


def test_lone_star_is_not_enough():
    """Одна жёлтая звёздочка (без слова «Музыка») — не повод считать, что открыт сайт плеера."""
    from PIL import Image
    from features import yamusic
    star = Image.open(yamusic.LOGO).convert("RGB").crop((0, 0, 64, 64))
    assert yamusic.logo_score(_scene((30, 20, 40), (star, (200, 100)))) < yamusic.LOGO_SCORE
