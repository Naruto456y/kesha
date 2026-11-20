"""Общий микрофон: детектор и запись команды читают один поток без дыр (без реального микрофона)."""
import numpy as np
import pytest

from voice import mic


class FakeStream:
    def __init__(self, callback=None, **k):
        self.callback = callback

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass


class Status:
    input_overflow = False


@pytest.fixture
def shared(monkeypatch):
    monkeypatch.setattr(mic.sd, "RawInputStream", FakeStream)
    monkeypatch.setattr(mic, "_shared", None)
    monkeypatch.setattr(mic, "_last_pos", None)
    m = mic.start_shared()
    yield m
    monkeypatch.setattr(mic, "_shared", None)


def feed(m, samples):
    x = np.asarray(samples, dtype=np.int16)
    m._stream.callback(x.tobytes(), len(x), None, Status())


def test_resume_continues_without_gap(shared):
    with mic.open_stream(16000, 4) as s:          # детектор «Кеша»
        feed(shared, range(10))
        assert s.read(4)[0] == np.arange(4, dtype=np.int16).tobytes()
    # звук, пришедший пока детектор отдавал управление, не теряется
    with mic.open_stream(16000, 4, resume=True) as s:
        assert s.read(6)[0] == np.arange(4, 10, dtype=np.int16).tobytes()


def test_fresh_stream_skips_old_audio(shared):
    feed(shared, range(10))
    with mic.open_stream(16000, 4) as s:          # без resume — только новый звук
        feed(shared, [100, 101])
        assert s.read(2)[0] == np.array([100, 101], dtype=np.int16).tobytes()


def test_ring_wraps(shared):
    size = len(shared._ring)
    feed(shared, np.zeros(size - 3))
    with mic.open_stream(16000, 4) as s:
        feed(shared, [1, 2, 3, 4, 5])
        assert s.read(5)[0] == np.array([1, 2, 3, 4, 5], dtype=np.int16).tobytes()


def test_other_rate_uses_own_stream(shared):
    assert isinstance(mic.open_stream(48000, 4), FakeStream)
