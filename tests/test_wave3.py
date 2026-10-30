"""Тесты волны 3: тихий режим, горячая клавиша, защита, звуки, уведомления, настройки."""
import wave

import pytest

import core
import notify
import security
import settings
from core import handle_command


# ---------- настройки ----------
def test_settings_persist_and_notify(tmp_path):
    seen = []
    cb = lambda k, v: seen.append((k, v))
    settings.subscribe(cb)
    try:
        assert settings.get("silent") is False            # значение по умолчанию
        settings.set("silent", True)
        settings.set("silent", True)                      # без изменений — без события
        assert seen == [("silent", True)]
        settings.use_file(tmp_path / "settings.json")      # «перезапуск»
        assert settings.get("silent") is True
    finally:
        settings.unsubscribe(cb)


# ---------- тихий режим ----------
@pytest.mark.parametrize("phrase,silent", [
    ("тихий режим", True), ("включи тихий режим", True), ("молчи", True),
    ("не говори вслух", True), ("говори вслух", False), ("выключи тихий режим", False),
    ("отключи режим молчания", False), ("можешь говорить", False),
])
def test_silent_mode_command(phrase, silent):
    settings.set("silent", not silent)
    handle_command(phrase, "test")
    assert settings.get("silent") is silent


def test_speaker_respects_silent_mode(monkeypatch):
    from voice.speaker import speaker
    calls = []

    def fake_synth(text):
        calls.append(text)
        raise RuntimeError("без звука в тестах")

    monkeypatch.setattr(speaker, "_synthesize", fake_synth)
    settings.set("silent", True)
    speaker.say("привет")
    assert calls == []                       # в тихом режиме даже не синтезируем
    speaker.say("привет", force=True)        # /say из Telegram — говорим всё равно
    assert calls == ["привет"]
    assert not speaker.is_speaking           # ошибка синтеза не оставила «говорю»


def test_messenger_beats_typing():
    import commands  # noqa: F401
    first = next(core._matching("напиши маме в телеграм что я дома"))
    assert first["name"] == "send_message"


# ---------- защита ----------
@pytest.mark.parametrize("phrase", ["открой командную строку", "запусти терминал",
                                    "открой редактор реестра", "открой powershell", "открой cmd"])
def test_blacklisted_apps_never_open(phrase, monkeypatch, tmp_path):
    import commands
    opened = []
    monkeypatch.setattr(commands.os, "startfile", lambda p: opened.append(p), raising=False)
    monkeypatch.setattr(commands.AppOpener, "open", lambda *a, **k: opened.append(a))
    reply = handle_command(phrase, "telegram")
    assert opened == []
    assert reply.startswith("Не буду открывать")
    assert "BLOCKED | telegram" in (tmp_path / "kesha.log").read_text(encoding="utf-8")


def test_open_app_does_not_launch_random_programs(monkeypatch):
    """Раньше AppOpener(match_closest=True) открывал «ближайшее» к любой бессмыслице."""
    import commands
    opened = []
    monkeypatch.setattr(commands.AppOpener, "give_appnames", lambda: {"google chrome": 1, "steam": 1}.keys())
    monkeypatch.setattr(commands.AppOpener, "open", lambda name, **k: opened.append(name))
    monkeypatch.setattr(commands.os, "startfile", lambda p: opened.append(p), raising=False)
    assert handle_command("запусти ту штуку с кубиками", "t") == "Не нашёл приложение «ту штуку с кубиками»"
    assert handle_command("открой chrome", "t") == "Открываю google chrome"
    assert handle_command("открой калькулятор", "t") == "Открываю калькулятор"
    assert opened == ["google chrome", "calc.exe"]


def test_whitelist(monkeypatch):
    monkeypatch.setattr(security, "SECURITY_ALLOWED_APPS", ["блокнот"])
    assert security.check_app("блокнот") is None
    assert "белом списке" in security.check_app("телеграм")


def test_dangerous_keys_and_text_blocked(monkeypatch):
    import commands
    sent, typed = [], []
    monkeypatch.setattr(commands.keyboard, "send", lambda k: sent.append(k))
    monkeypatch.setattr(commands.keyboard, "write", lambda t: typed.append(t))
    assert handle_command("нажми клавишу win+r", "test").startswith("Не буду")
    assert handle_command("напечатай rmdir /s /q c:\\windows", "test").startswith("Не буду")
    assert handle_command("напечатай format c:", "test").startswith("Не буду")
    assert sent == [] and typed == []
    assert handle_command("нажми клавишу enter", "test") == "Нажал enter"
    assert handle_command("напечатай привет мир", "test") == "Напечатал: привет мир"


def test_protected_paths():
    assert security.is_protected_path("C:/Windows/System32")
    assert security.is_protected_path("C:/")
    assert security.is_protected_path("C:/Program Files/Anything")
    assert not security.is_protected_path(__file__)
    assert security.check_delete("C:/Windows") is not None


# ---------- звуки ----------
def test_sfx_files_generated(tmp_path, monkeypatch):
    from voice import sfx
    monkeypatch.setattr(sfx, "SOUNDS_DIR", tmp_path / "sounds")
    for name in sfx.TONES:
        path = sfx.sound_path(name)
        with wave.open(str(path)) as w:
            assert w.getframerate() == sfx.RATE
            assert abs(w.getnframes() / sfx.RATE - sfx.duration(name)) < 0.01


def test_sfx_respects_setting(monkeypatch):
    from voice import sfx
    played = []
    monkeypatch.setattr(sfx, "_cache", {"wake": type("S", (), {"play": lambda self: played.append(1)})()})
    monkeypatch.setattr(sfx, "_mixer", lambda: None)
    settings.set("sounds", False)
    sfx.play("wake")
    assert played == []
    settings.set("sounds", True)
    sfx.play("wake")
    assert played == [1]


# ---------- уведомления ----------
def test_announce_goes_to_ui_and_notification(monkeypatch):
    shown, events = [], []
    notify.add_listener(lambda t, m: shown.append((t, m)))
    core.subscribe(lambda s, t, r: events.append((s, r)))
    monkeypatch.setitem(__import__("sys").modules, "voice", type("V", (), {"say": staticmethod(lambda t: None)}))
    core.announce("Напоминаю: чай", title="Напоминание")
    assert ("Напоминание", "Напоминаю: чай") in shown
    assert ("kesha", "Напоминаю: чай") in events


# ---------- голосовой цикл: Ctrl+Space, wake word, ошибки ----------
class FakeVAD:
    def __init__(self, phrases):
        self.phrases = list(phrases)
        self.last_info = {}

    def record(self, max_wait=None, should_pause=None):
        if not self.phrases:
            return b""
        audio = self.phrases.pop(0)
        self.last_info = {"duration_sec": 0.5}
        return audio


class FakeRec:
    def recognize(self, audio):
        return audio.decode("utf-8") if audio else ""


@pytest.fixture
def loop(monkeypatch):
    from voice import listener
    said, sounds, handled = [], [], []
    monkeypatch.setattr(listener, "say", lambda t: said.append(t))
    monkeypatch.setattr(listener, "is_mic_blocked", lambda: False)
    monkeypatch.setattr(listener.sfx, "play", lambda n: sounds.append(n))
    monkeypatch.setattr(listener.sfx, "wait_quiet", lambda *a: None)
    monkeypatch.setattr(listener.sfx, "alarm_stop", lambda: False)
    monkeypatch.setattr(listener, "handle_command",
                        lambda t, source, ai=True: handled.append(t) or ("Не понял команду." if t == "абракадабра" else "ок"))

    def make(phrases, ww=None):
        vl = listener.VoiceLoop(FakeRec(), FakeVAD([p.encode("utf-8") for p in phrases]), ww)
        vl.shout.check = lambda audio: False
        return vl
    return make, said, sounds, handled


def test_wake_word_by_text(loop):
    make, said, sounds, handled = loop
    vl = make(["кеша который час"])
    vl.step()
    assert handled == ["который час"] and said == ["ок"] and "wake" in sounds


def test_misheard_wake_word_at_start(loop):
    """GigaAM иногда слышит «Кеша» как «каша»: в начале фразы это активатор, в середине — нет."""
    make, said, sounds, handled = loop
    make(["каша который час"]).step()
    assert handled == ["который час"]
    handled.clear()
    make(["на завтрак была каша"]).step()
    assert handled == []


def test_heard_phrases_are_logged(loop, tmp_path):
    make, said, sounds, handled = loop
    make(["какой-то разговор рядом"]).step()
    log = (tmp_path / "kesha.log").read_text(encoding="utf-8")
    assert "HEARD | voice | какой-то разговор рядом" in log and "wake=нет" in log


def test_speech_without_wake_word_ignored(loop):
    make, said, sounds, handled = loop
    make(["который час"]).step()
    assert handled == []


def test_hotkey_without_wake_word(loop):
    make, said, sounds, handled = loop
    vl = make(["который час"])
    vl.arm()                      # Ctrl+Space
    vl.step()
    assert handled == ["который час"]
    assert sounds[0] == "wake"


def test_hotkey_expires(loop, monkeypatch):
    from voice import listener
    make, said, sounds, handled = loop
    vl = make(["который час"])
    vl.arm()
    monkeypatch.setattr(listener, "ARM_TIMEOUT", -10)
    vl.step()
    assert handled == []


def test_hotkey_silence_returns_to_idle(loop, monkeypatch):
    """Нажали Ctrl+Space и молчат — реактор не висит в «СЛУШАЮ» вечно."""
    from voice import listener
    import state_manager
    make, *_ = loop
    states = []
    cb = lambda p: states.append(p["state"])
    state_manager.subscribe(cb)
    try:
        vl = make([])
        vl.arm()
        stamp = vl._armed_at
        vl.vad.speech_active = True          # фраза ещё пишется — не трогаем
        monkeypatch.setattr(vl, "_schedule_expiry", lambda s, d: None)
        vl._expire_arm(stamp)
        assert vl._armed_at == stamp
        vl.vad.speech_active = False
        vl._expire_arm(stamp)
        assert vl._armed_at is None and states[-1] == "IDLE"
    finally:
        state_manager.unsubscribe(cb)


def test_hotkey_with_porcupine(loop):
    make, said, sounds, handled = loop

    class WW:
        stopped = False

        def stop(self):
            self.stopped = True

        def wait_for_wake(self, should_pause=None):
            raise AssertionError("не должны ждать слово — клавиша уже нажата")

    ww = WW()
    vl = make(["открой ютуб"], ww=ww)
    vl.arm()
    assert ww.stopped
    vl.step()
    assert handled == ["открой ютуб"]


def test_background_speech_does_not_reach_gigachat(loop, monkeypatch):
    """Живой случай: фоновое видео «ребята теай» через GigaChat стало «скролл вниз»."""
    from voice import listener
    make, said, sounds, handled = loop
    calls = []
    monkeypatch.setattr(listener, "handle_command",
                        lambda t, source, ai=True: calls.append((t, ai)) or ("ок" if ai else ""))
    vl = make(["кеша который час", "ребята теай", "кеша а какая погода"])
    vl.step()
    assert calls == [("который час", True), ("ребята теай", False), ("а какая погода", True)]
    assert said == ["ок", "ок"]            # на фон не отвечаем вслух


def test_wake_then_pause_then_command_uses_ai(loop, monkeypatch):
    from voice import listener
    make, said, sounds, handled = loop
    calls = []
    monkeypatch.setattr(listener, "handle_command", lambda t, source, ai=True: calls.append((t, ai)) or "ок")
    make(["кеша", "какая столица франции"]).step()
    assert calls == [("какая столица франции", True)]


def test_max_length_recording_is_noise(loop):
    make, said, sounds, handled = loop
    vl = make(["ребята тест это видео которое играет без пауз"])
    real_record = vl.vad.record

    def record(**kw):
        audio = real_record(**kw)
        vl.vad.last_info = {"stopped_by": "max", "duration_sec": 15.0}
        return audio
    vl.vad.record = record
    vl.step()
    assert handled == []


def test_core_without_ai_ignores_unknown(monkeypatch):
    import commands  # noqa: F401
    monkeypatch.setattr(core, "ai_ask", lambda t: "CMD: скролл вниз")
    assert handle_command("ребята теай", "voice", ai=False) == ""
    assert handle_command("который час", "voice", ai=False).startswith("Сейчас")


def test_error_reply_plays_boop(loop):
    make, said, sounds, handled = loop
    make(["кеша абракадабра"]).step()
    assert "error" in sounds and said == ["Не понял команду."]


def test_hotkey_stops_ringing_alarm(loop, monkeypatch):
    from voice import listener
    make, said, sounds, handled = loop
    monkeypatch.setattr(listener.sfx, "alarm_stop", lambda: True)
    vl = make([])
    vl.arm()
    assert vl._armed_at is None and sounds == []


# ---------- по логу пользователя ----------
def test_mixed_script_from_gigaam():
    """Живой лог: GigaAM написал «открой youтube» (т — кириллическая)."""
    from nlu import fix_mixed_script
    assert fix_mixed_script("открой youтube") == "открой youtube"
    assert fix_mixed_script("открой telegrаm") == "открой telegram"
    assert fix_mixed_script("привет world") == "привет world"      # разные слова — не трогаем
    assert fix_mixed_script("кеша привет") == "кеша привет"


def test_youtube_with_mixed_letters_opens_youtube(monkeypatch):
    import commands
    opened = []
    monkeypatch.setattr(commands.webbrowser, "open", lambda url, *a, **k: opened.append(url))
    assert handle_command("открой youтube", "voice") != ""
    assert opened == ["https://youtube.com"]


def test_wake_word_over_background_video(loop):
    """Видео играет без пауз (запись упирается в 15 с), а пользователь говорит «Кеша, ...» поверх."""
    make, said, sounds, handled = loop
    vl = make(["каждый зарабатывает тысячу долларов кеша открой телеграм"])
    real = vl.vad.record

    def record(**kw):
        audio = real(**kw)
        vl.vad.last_info = {"stopped_by": "max", "duration_sec": 15.0}
        return audio
    vl.vad.record = record
    vl.step()
    assert handled == ["открой телеграм"]          # фон отрезан, команда выполнена


def test_pure_background_video_ignored(loop, tmp_path):
    make, said, sounds, handled = loop
    vl = make(["в месяц с целой командой аниматоров и это не единственный пример"])
    real = vl.vad.record

    def record(**kw):
        audio = real(**kw)
        vl.vad.last_info = {"stopped_by": "max", "duration_sec": 15.0}
        return audio
    vl.vad.record = record
    vl.step()
    assert handled == [] and said == []
    assert "(фон)" in (tmp_path / "kesha.log").read_text(encoding="utf-8")


def test_long_background_phrase_without_wake_ignored(loop):
    """Видео рядом: длинная фраза без «Кеша» в активном окне не должна выполнять команды."""
    make, said, sounds, handled = loop
    make(["кеша который час", "экономить на том сверни окно чуть позже в этом видео я покажу"]).step()
    assert handled == ["который час"]
