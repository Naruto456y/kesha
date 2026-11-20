"""Перебивание Кеши словом «Кеша» и клавишей, Silero VAD в записи фразы, шумодав."""
import numpy as np
import pytest

import settings


class _VAD:
    def __init__(self, phrases):
        self.phrases, self.starts, self.last_info = list(phrases), [], {}

    def record(self, max_wait=None, should_pause=None, start_audio=None):
        self.starts.append(start_audio)
        self.last_info = {"duration_sec": 0.5}
        return self.phrases.pop(0).encode("utf-8") if self.phrases else b""


class _WW:
    """Первый вызов — обычное «Кеша»; вызовы с timeout — ожидание перебивания во время ответа."""
    supports_on_wake = True

    def __init__(self, barge):
        self.wake_audio, self.barge, self.barge_calls = None, list(barge), 0

    def wait_for_wake(self, timeout=None, should_pause=None, on_wake=None):
        if timeout is not None:
            self.barge_calls += 1
            if not (self.barge.pop(0) if self.barge else False):
                return False
        self.wake_audio = np.ones(160, dtype=np.int16)
        if on_wake:
            on_wake()
        return True

    def stop(self):
        pass


@pytest.fixture
def loop(monkeypatch):
    from voice import listener
    calls, said, stopped = [], [], []
    settings.set("barge_in", True)
    monkeypatch.setattr(listener, "say", said.append)
    monkeypatch.setattr(listener, "is_mic_blocked", lambda: False)
    monkeypatch.setattr(listener, "speech_left", lambda: 3.0)
    monkeypatch.setattr(listener, "stop_speaking", lambda: stopped.append(1) or True)
    monkeypatch.setattr(listener.sfx, "play", lambda n: None)
    monkeypatch.setattr(listener.sfx, "wait_quiet", lambda *a: None)
    monkeypatch.setattr(listener, "handle_command", lambda t, source, ai=True: calls.append((t, ai)) or "вот длинный ответ")

    class Rec:
        def recognize(self, audio):
            return audio.decode("utf-8") if audio else ""

    def make(phrases, barge):
        vl = listener.VoiceLoop(Rec(), _VAD(phrases), _WW(barge))
        vl.shout.check = lambda a: False
        return vl
    return make, calls, said, stopped


def test_barge_in_stops_speech_and_takes_next_command(loop):
    make, calls, said, stopped = loop
    vl = make(["кеша расскажи анекдот", "кеша сделай тише"], barge=[True, False])
    vl.step()
    assert stopped                                           # замолчала на полуслове
    assert calls == [("расскажи анекдот", True), ("сделай тише", True)]   # вторая — как после «Кеша»
    assert vl.vad.starts[1] is not None                      # запись продолжила звук с «Кеша»


def test_barge_in_stop_word_only_silences(loop):
    make, calls, said, stopped = loop
    vl = make(["кеша расскажи анекдот", "кеша стоп"], barge=[True])
    vl.step()
    assert stopped and calls == [("расскажи анекдот", True)]     # «стоп» командой не стало
    assert len(said) == 1


def test_no_barge_when_setting_off(loop):
    make, calls, said, stopped = loop
    settings.set("barge_in", False)
    vl = make(["кеша который час"], barge=[True])
    vl.step()
    assert vl.ww.barge_calls == 0 and not stopped


def test_no_barge_when_kesha_says_her_name(loop, monkeypatch):
    """В ответе есть «Кеша» — микрофон не слушаем, иначе она перебьёт сама себя."""
    from voice import listener
    make, calls, said, stopped = loop
    monkeypatch.setattr(listener, "handle_command", lambda t, source, ai=True: "Меня зовут Кеша")
    vl = make(["кеша как тебя зовут"], barge=[True])
    vl.step()
    assert vl.ww.barge_calls == 0 and not stopped


def test_short_reply_not_interruptible(loop, monkeypatch):
    from voice import listener
    make, calls, said, stopped = loop
    monkeypatch.setattr(listener, "speech_left", lambda: 0.2)
    vl = make(["кеша привет"], barge=[True])
    vl.step()
    assert vl.ww.barge_calls == 0


def test_hotkey_interrupts_speech(loop, monkeypatch):
    from voice import listener
    make, calls, said, stopped = loop
    monkeypatch.setattr(listener.duck, "duck", lambda: None)
    vl = make([], barge=[])
    vl.arm()
    assert stopped


def test_speaker_stop_unblocks_mic(monkeypatch):
    import sys
    import time
    import voice.speaker  # noqa: F401
    sp = sys.modules["voice.speaker"]     # voice.speaker из пакета — это объект диктора, не модуль
    monkeypatch.setattr(sp.pygame.mixer.music, "stop", lambda: None)
    monkeypatch.setattr(sp.pygame.mixer.music, "unload", lambda: None)
    s = sp.speaker
    gen = s._gen
    s.is_speaking, s.mic_blocked_until = True, time.time() + 30
    assert s.speech_left() > 29
    assert s.stop() is True
    assert not s.is_mic_blocked() and not s.is_speaking and s._gen == gen + 1
    assert s.stop() is False                                  # прерывать уже нечего


# ---------- Silero VAD ----------
def test_recorder_uses_silero_when_enabled(monkeypatch):
    import config
    from voice import silero_gate, vad_recorder

    class Gate:
        def __init__(self):
            self.fed, self.resets = 0, 0

        def reset(self):
            self.resets += 1

        def is_speech(self, frame):
            self.fed += 1
            return frame[:2] != b"\x00\x00"

    gate = Gate()
    monkeypatch.setattr(config, "VAD_ENGINE", "silero")
    monkeypatch.setattr(silero_gate, "load", lambda thr=0.5: gate)
    rec = vad_recorder.VADRecorder(min_db=-64)
    loud = (np.ones(480) * 8000).astype(np.int16).tobytes()
    assert rec._is_speech(loud) is True
    assert rec._is_speech(bytes(960)) is False
    assert gate.fed == 2                                      # тихий кадр тоже ушёл в сеть


def test_recorder_falls_back_without_silero(monkeypatch):
    import config
    from voice import silero_gate, vad_recorder
    monkeypatch.setattr(config, "VAD_ENGINE", "silero")
    monkeypatch.setattr(silero_gate, "load", lambda thr=0.5: None)
    rec = vad_recorder.VADRecorder()
    assert rec.silero is None
    assert rec._is_speech(bytes(960)) is False


def test_silero_gate_real_model_ignores_noise():
    """Настоящая модель: шум и ровный тон — не речь (webrtcvad считал их речью)."""
    silero_gate = pytest.importorskip("voice.silero_gate")
    pytest.importorskip("silero_vad")
    gate = silero_gate.load()
    assert gate is not None
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 1500, 16000 * 2).astype(np.int16).tobytes()
    hits = [gate.is_speech(noise[i:i + 960]) for i in range(0, len(noise) - 959, 960)]
    assert sum(hits) == 0


# ---------- шумодав ----------
def test_denoise_keeps_length_and_cuts_noise():
    from voice.denoise import denoise
    rng = np.random.default_rng(1)
    t = np.arange(16000 * 2) / 16000
    voice = np.where((t > 0.5) & (t < 1.5), 6000 * np.sin(2 * np.pi * 300 * t), 0)
    noisy = (voice + rng.normal(0, 400, len(t))).astype(np.int16)
    out = np.frombuffer(denoise(noisy.tobytes()), dtype=np.int16).astype(np.float32)
    assert len(out) == len(noisy)
    rms = lambda x: float(np.sqrt(np.mean(x ** 2)))           # noqa: E731
    assert rms(out[:6000]) < rms(noisy[:6000].astype(np.float32)) * 0.7      # тишина стала тише
    assert rms(out[9000:23000]) > rms(noisy[9000:23000].astype(np.float32)) * 0.8   # голос остался


def test_denoise_short_audio_untouched():
    from voice.denoise import denoise
    short = bytes(3200)
    assert denoise(short) is short
