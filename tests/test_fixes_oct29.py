"""Правки 29.10 (вечер): клавиши по-русски, сайты вместо «не нашёл приложение», батарея,
латиница в Silero, «Кеша, команда» одним духом, вопрос после поиска, сон."""
import numpy as np
import pytest

import commands
import core
from core import handle_command


# ---------- клавиши ----------
@pytest.mark.parametrize("spoken,key", [
    ("эntr", "enter"), ("энтер", "enter"), ("ентра", "enter"), ("контрол плюс c", "ctrl+c"),
    ("стрелка вверх", "up"), ("alt+f4", "alt+f4"), ("ф5", "f5"), ("шифт таб", "shift+tab"),
    ("пробел", "space"), ("вин r", "win+r"),
])
def test_key_combo(spoken, key):
    assert commands.key_combo(spoken) == key


def test_press_key_russian_name(monkeypatch):
    sent = []
    monkeypatch.setattr(commands.keyboard, "send", lambda k: sent.append(k))
    assert commands.press_key("нажми эntr") == "Нажал enter"
    assert sent == ["enter"]


def test_win_r_still_blocked_after_mapping(monkeypatch):
    sent = []
    monkeypatch.setattr(commands.keyboard, "send", lambda k: sent.append(k))
    assert "запрещено" in commands.press_key("нажми вин плюс r") and sent == []


def test_bare_enter_command(monkeypatch):
    sent = []
    monkeypatch.setattr(commands.keyboard, "send", lambda k: sent.append(k))
    assert handle_command("энтер", "t", ai=False) == "Нажал enter" and sent == ["enter"]


# ---------- сайты и VS Code ----------
def test_unknown_app_that_sounds_like_youtube_opens_site(monkeypatch):
    opened = []
    monkeypatch.setattr(commands.webbrowser, "open", lambda u: opened.append(u))
    monkeypatch.setattr(commands.app_index, "find", lambda a: None)
    monkeypatch.setattr(commands, "_closest_app", lambda a: None)
    assert commands.open_app("открой ruтube") == "Открываю YouTube"
    assert opened == ["https://www.youtube.com"]


def test_unknown_app_still_not_found(monkeypatch):
    monkeypatch.setattr(commands.app_index, "find", lambda a: None)
    monkeypatch.setattr(commands, "_closest_app", lambda a: None)
    assert commands.open_app("открой зюзюблик") == "Не нашёл приложение «зюзюблик»"


@pytest.mark.parametrize("phrase", ["открой vs кот", "открой wes cote", "открой bascod", "vs код"])
def test_vscode_mishearings(phrase):
    names = [c["name"] for c in core._matching(phrase)]
    assert names and names[0] == "open_vscode"


# ---------- батарея ----------
@pytest.mark.parametrize("plugged,word", [(True, "Батарея заряжается"), (False, "Батарея не заряжается")])
def test_battery_wording(monkeypatch, plugged, word):
    b = type("B", (), {"power_plugged": plugged, "percent": 80})()
    monkeypatch.setattr(commands.psutil, "sensors_battery", lambda: b)
    assert commands.get_battery("батарея") == f"{word}. Уровень: 80%"


# ---------- латиница больше не уводит в gTTS ----------
def test_latin_read_in_russian():
    from voice.text_norm import latin_to_ru
    assert latin_to_ru("Открываю YouTube") == "Открываю ютуб"
    assert latin_to_ru("Нажал Enter") == "Нажал энтер"
    assert latin_to_ru("USB") == "ю эс би"


def test_silero_first_for_latin_text():
    from voice import tts_engines
    assert tts_engines.engine_order("male", "ru")[0][0] == "silero"


def test_silero_chunks_long_text():
    from voice.tts_engines import _chunks
    parts = _chunks("Привет. " * 300)
    assert len(parts) > 1 and all(len(p) <= 800 for p in parts)


# ---------- вопрос после поиска ----------
def test_search_asks_and_yes_opens_first_link(monkeypatch):
    from features import web
    opened = []
    monkeypatch.setattr(web, "open_first", lambda q: opened.append(q) or "Открываю первую ссылку")
    r = handle_command("найди рецепт борща", "t")
    assert r.endswith("Открыть первую ссылку?")
    assert handle_command("да", "t") == "Открываю первую ссылку" and opened == ["рецепт борща"]
    assert handle_command("да", "t") != "Открываю первую ссылку"     # вопрос уже закрыт


def test_search_no_answer(monkeypatch):
    from features import web
    monkeypatch.setattr(web, "open_first", lambda q: pytest.fail("не должны открывать"))
    handle_command("найди рецепт борща", "t")
    assert handle_command("нет", "t") == "Ок"


def test_question_expires(monkeypatch):
    called = []
    token = core._source.set("t")
    try:
        core.ask_yes_no(lambda: called.append(1) or "сделал", ttl=-1)
    finally:
        core._source.reset(token)
    handle_command("да", "t")
    assert called == []


# ---------- сон ----------
def test_sleep_uses_modern_standby(monkeypatch):
    import ctypes
    calls = []
    monkeypatch.setattr(commands, "_modern_standby", lambda: True)
    monkeypatch.setattr(ctypes.windll.user32, "PostMessageW", lambda *a: calls.append(("screen", a[3])))
    monkeypatch.setattr(ctypes.windll.powrprof, "SetSuspendState", lambda *a: calls.append(("suspend",)))
    monkeypatch.setattr(commands.threading, "Timer", lambda d, fn: type("T", (), {"start": lambda s: fn()})())
    commands._sleep_later(0)
    assert calls == [("screen", 2)]


# ---------- «Кеша, открой браузер» одним духом ----------
class _WakeVAD:
    def __init__(self, phrases):
        self.phrases, self.starts, self.last_info = list(phrases), [], {}

    def record(self, max_wait=None, should_pause=None, start_audio=None):
        self.starts.append(start_audio)
        self.last_info = {"duration_sec": 0.5}
        return self.phrases.pop(0).encode("utf-8") if self.phrases else b""


class _WakeWW:
    supports_on_wake = True

    def __init__(self):
        self.wake_audio = None

    def wait_for_wake(self, should_pause=None, on_wake=None):
        self.wake_audio = np.ones(160, dtype=np.int16)
        on_wake()
        return True

    def stop(self):
        pass


@pytest.fixture
def wake_loop(monkeypatch):
    from voice import listener
    calls = []
    monkeypatch.setattr(listener, "say", lambda t: None)
    monkeypatch.setattr(listener, "is_mic_blocked", lambda: False)
    monkeypatch.setattr(listener.sfx, "play", lambda n: None)
    monkeypatch.setattr(listener.sfx, "wait_quiet", lambda *a: None)
    monkeypatch.setattr(listener, "handle_command", lambda t, source, ai=True: calls.append((t, ai)) or "ок")

    class Rec:
        def recognize(self, audio):
            return audio.decode("utf-8") if audio else ""

    def make(phrases):
        vl = listener.VoiceLoop(Rec(), _WakeVAD(phrases), _WakeWW())
        vl.shout.check = lambda a: False
        return vl
    return make, calls


def test_command_in_one_breath_continues_wake_audio(wake_loop):
    make, calls = wake_loop
    vl = make(["ну вот кеша открой браузер"])
    vl.step()
    assert calls == [("открой браузер", True)]
    assert vl.vad.starts[0] is not None and vl.vad.starts[1] is None   # первая запись — с «Кеша»


def test_only_wake_word_then_command_still_uses_ai(wake_loop):
    make, calls = wake_loop
    vl = make(["кеша", "который час"])
    vl.step()
    assert calls == [("который час", True)]


def test_vad_continues_start_audio(monkeypatch):
    """Начало («Кеша, откр…») уже записано — VAD пишет дальше без ожидания речи."""
    from voice import vad_recorder
    loud = (np.sin(np.arange(480 * 20) / 3) * 8000).astype(np.int16).tobytes()
    quiet = bytes(960)

    class Stream:
        def __init__(self, *a, **k):
            self.n = 0

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            self.n += 1
            return (quiet, False)

    monkeypatch.setattr(vad_recorder.sd, "RawInputStream", Stream)
    rec = vad_recorder.VADRecorder()
    rec._is_speech = lambda f: f != quiet
    rec.min_db = -200
    audio = rec.record(max_wait=1, start_audio=loud)
    assert audio.startswith(loud[:960]) and rec.last_info["stopped_by"] == "silence"
