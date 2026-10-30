"""Тесты волны 5: язык, время суток, интонация, статистика, темы, голоса."""
import time
from datetime import datetime, timedelta

import numpy as np
import pytest

import core
import persona
import settings
from core import handle_command


class FakeGiga:
    def __init__(self, fn):
        self.fn = fn
        self.prompts = []

    def chat(self, prompt):
        self.prompts.append(prompt)
        return self.fn(prompt)


# ---------- мультиязычность ----------
def test_switch_language_and_translate(monkeypatch):
    giga = FakeGiga(lambda p: "It is 15:10" if "Переведи" in p else "Paris")
    monkeypatch.setattr(core, "_gig", giga)
    monkeypatch.setattr(core, "AI_AVAILABLE", True)
    assert handle_command("переключись на английский", "t").startswith("Switched to English")
    assert settings.get("language") == "en"

    import commands
    monkeypatch.setattr(commands, "datetime", type("D", (), {"now": staticmethod(lambda: datetime(2026, 1, 1, 15, 10))}))
    assert handle_command("который час", "t") == "It is 15:10"          # ответ команды переведён
    assert handle_command("который час", "t") == "It is 15:10"
    assert sum("Переведи" in p for p in giga.prompts) == 1                # перевод из кэша
    assert handle_command("столица франции", "t") == "Paris"
    assert "Отвечай на английском" in giga.prompts[-1]

    assert handle_command("переключись на русский", "t") == "Перешёл на русский."
    assert settings.get("language") == "ru"


def test_english_without_gigachat_keeps_russian(monkeypatch):
    monkeypatch.setattr(core, "AI_AVAILABLE", False)
    settings.set("language", "en")
    assert handle_command("спасибо", "t") != ""   # не падает, отвечает как может


def test_tts_uses_english_engine():
    from voice import tts_engines
    names = [n for n, _ in tts_engines.engine_order("male", "en")]
    assert names[0] == "google" and "silero" not in names


# ---------- время суток ----------
@pytest.mark.parametrize("hour,part", [(7, "morning"), (13, "day"), (20, "evening"), (2, "night"), (23, "night")])
def test_part_of_day(hour, part):
    assert persona.part_of_day(datetime(2026, 10, 23, hour)) == part


def test_greeting_depends_on_time():
    assert persona.greeting(datetime(2026, 1, 1, 8)).startswith("Доброе утро")
    assert persona.greeting(datetime(2026, 1, 1, 21)).startswith("Добрый вечер")
    for h in (2, 8, 13, 21):                       # одно приветствие: без «как дела» и «пора спать»
        g = persona.greeting(datetime(2026, 1, 1, h))
        assert "спать" not in g and "?" not in g and g.count("!") == 1
    assert persona.startup_phrase(datetime(2026, 1, 1, 13)).endswith("Готов к работе.")


# ---------- интонация ----------
def _speech(db, seconds=1.0):
    rate = 16000
    t = np.arange(int(rate * seconds)) / rate
    amp = 10 ** (db / 20) * np.sqrt(2)
    return (np.sin(2 * np.pi * 220 * t) * amp * 32767).astype(np.int16).tobytes()


def test_speech_db():
    from voice.loudness import speech_db
    assert abs(speech_db(_speech(-20)) - (-20)) < 0.5
    assert speech_db(b"") == -120.0


def test_shout_detector():
    from voice.loudness import ShoutDetector
    d = ShoutDetector(threshold_db=-14, margin_db=9)
    for _ in range(5):
        assert not d.check(_speech(-28))       # обычная речь
    assert d.check(_speech(-6))                # крик
    assert not d.check(_speech(-26))
    loud_room = ShoutDetector(threshold_db=-14, margin_db=9)
    for _ in range(5):
        assert not loud_room.check(_speech(-12))   # человек всегда говорит громко — это не крик
    assert not loud_room.check(_speech(-8))


def test_voice_loop_shout_reply(monkeypatch):
    from voice import listener
    said = []
    monkeypatch.setattr(listener, "say", lambda t: said.append(t))
    monkeypatch.setattr(listener, "is_mic_blocked", lambda: False)
    monkeypatch.setattr(listener.sfx, "play", lambda n: None)
    monkeypatch.setattr(listener.sfx, "wait_quiet", lambda *a: None)
    monkeypatch.setattr(listener, "handle_command", lambda t, source, ai=True: "Сейчас 15:10")
    vl = listener.VoiceLoop(None, None, None)
    vl._last_audio = _speech(-3)
    vl.shout.check = lambda audio: True
    vl._process("который час")
    assert said == [f"{listener.SHOUT_REPLY} Сейчас 15:10"]


# ---------- статистика ----------
def test_stats_counts_commands(monkeypatch):
    from features import stats
    import commands
    monkeypatch.setattr(commands.webbrowser, "open", lambda *a, **k: None)
    monkeypatch.setattr(commands.AppOpener, "open", lambda *a, **k: None)
    for _ in range(3):
        handle_command("включи музыку", "voice")
    handle_command("открой ютуб", "app")
    stats.record("voice", "play_music", ts=time.time() - 10 * 86400)   # давно — не в неделе

    assert handle_command("сколько раз ты включала музыку за неделю", "t") == \
        "«Включить музыку» — 3 раза за неделю."
    assert handle_command("сколько раз ты включала музыку за всё время", "t") == \
        "«Включить музыку» — 4 раза за всё время."
    assert handle_command("сколько раз я открывал ютуб сегодня", "t") == "«Открыть YouTube» — 1 раз сегодня."
    top = handle_command("статистика", "t")
    assert top.startswith("За неделю всего") and "Включить музыку — 3" in top


def test_stats_unknown_command_goes_to_ai(monkeypatch):
    monkeypatch.setattr(core, "ai_ask", lambda t: "ответ ИИ")
    assert handle_command("сколько раз в неделю нужно бегать", "t") == "ответ ИИ"


# ---------- темы, голоса, значок, звуки ----------
@pytest.mark.parametrize("phrase,theme", [
    ("включи светлую тему", "light"), ("тёмная тема", "dark"), ("светлая тема", "light"),
    ("ночная тема", "dark"),
])
def test_theme(phrase, theme):
    handle_command(phrase, "t")
    assert settings.get("theme") == theme


def test_theme_toggle():
    settings.set("theme", "dark")
    handle_command("смени тему", "t")
    assert settings.get("theme") == "light"


def test_light_theme_is_not_light_switch():
    first = next(core._matching("включи светлую тему"))
    assert first["name"] == "switch_theme"


@pytest.mark.parametrize("phrase,voice", [
    ("мужской голос", "male"), ("говори женским голосом", "female"),
    ("голос робота", "robot"), ("стандартный голос", "google"),
])
def test_voice_switch(phrase, voice):
    handle_command(phrase, "t")
    assert settings.get("voice") == voice


def test_voice_cycle_and_query():
    settings.set("voice", "google")
    handle_command("смени голос", "t")
    assert settings.get("voice") == "female"
    assert handle_command("какой у тебя голос", "t") == "Сейчас голос: женский."


def test_floating_and_sounds_toggles():
    handle_command("скрой значок", "t")
    assert settings.get("floating_icon") is False
    handle_command("покажи значок", "t")
    assert settings.get("floating_icon") is True
    handle_command("выключи звуки", "t")
    assert settings.get("sounds") is False
    handle_command("включи звуки", "t")
    assert settings.get("sounds") is True


# ---------- движки озвучки ----------
def test_engine_order():
    from voice import tts_engines
    assert [n for n, _ in tts_engines.engine_order("google", "ru")] == ["google", "silero", "sapi"]
    assert [n for n, _ in tts_engines.engine_order("robot", "ru")][0] == "silero"


def test_speaker_falls_back_to_next_engine(monkeypatch):
    from voice import tts_engines
    from voice.speaker import speaker

    def broken(text):
        raise OSError("нет интернета")
    monkeypatch.setattr(tts_engines, "engine_order",
                        lambda voice, lang: [("google", broken), ("silero", lambda t: "x.wav")])
    assert speaker._synthesize("привет") == "x.wav" and speaker.last_engine == "silero"


def test_text_normalization_for_silero():
    from voice.text_norm import normalize_for_tts, number_to_words
    assert number_to_words(2026) == "две тысячи двадцать шесть"
    assert number_to_words(101) == "сто один"
    assert number_to_words(1_000_000) == "один миллион"
    assert normalize_for_tts("Сейчас 19:05") == "Сейчас девятнадцать ноль пять"
    assert normalize_for_tts("Громкость 35%") == "Громкость тридцать пять процентов"
    assert normalize_for_tts("Москва: 12°C") == "Москва: двенадцать градусов"
    assert normalize_for_tts("2 часа") == "два часа"


def test_robot_effect_keeps_length_and_level():
    from voice.tts_engines import robotize
    x = np.sin(np.linspace(0, 100, 48000)).astype(np.float32) * 0.5
    y = robotize(x, 48000)
    assert len(y) == len(x) and 0.8 < np.max(np.abs(y)) <= 0.91
