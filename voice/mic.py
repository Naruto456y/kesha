"""Общий микрофон: один поток пишет в кольцевой буфер, детектор «Кеша» и запись команды читают из него.
Раньше каждый открывал свой поток: на стыке «Кеша» -> команда терялось 50–200 мс, а пока
GigaAM проверял «Кеша», микрофон никто не читал и буфер переполнялся — «сверни» превращалось в «кни».

open_stream(rate, blocksize, device, resume) — то же, что sd.RawInputStream (with/read),
но если общий микрофон запущен (start_shared), читает из него. resume=True — продолжить
ровно с места, где закончилось прошлое чтение (запись команды после детектора)."""
import threading
import time

import numpy as np
import sounddevice as sd

RATE = 16000
BLOCK = 160              # 10 мс на вызов колбэка
KEEP_SEC = 20            # столько звука держим: хватает, даже если проверка GigaAM задержалась

_shared = None
_last_pos = None         # где остановилось последнее чтение из общего микрофона
_last_at = 0.0
RESUME_SEC = 1.0         # продолжаем, только если прошлое чтение закончилось только что


class SharedMic:
    def __init__(self, device=None, rate=RATE, keep_sec=KEEP_SEC):
        self.rate = rate
        self.device = device
        self._ring = np.zeros(int(keep_sec * rate), dtype=np.int16)
        self.total = 0           # сколько сэмплов записано с запуска
        self.overflows = 0
        self._cond = threading.Condition()
        self._stream = sd.RawInputStream(samplerate=rate, blocksize=BLOCK, channels=1,
                                         dtype="int16", device=device, callback=self._callback)
        self._stream.start()

    def _callback(self, indata, frames, time_info, status):
        if status.input_overflow:
            self.overflows += 1
        x = np.frombuffer(bytes(indata), dtype=np.int16)
        size = len(self._ring)
        with self._cond:
            i = self.total % size
            first = min(len(x), size - i)
            self._ring[i:i + first] = x[:first]
            self._ring[:len(x) - first] = x[first:]
            self.total += len(x)
            self._cond.notify_all()

    def read(self, pos, n, timeout=3.0):
        """n сэмплов с позиции pos (ждёт, пока накопятся) -> (bytes, новая позиция)."""
        with self._cond:
            if not self._cond.wait_for(lambda: self.total >= pos + n, timeout):
                raise RuntimeError("микрофон не присылает звук")
            pos = max(pos, self.total - len(self._ring))   # отстали больше буфера — без старья
            idx = np.arange(pos, pos + n) % len(self._ring)
            return self._ring[idx].tobytes(), pos + n

    def close(self):
        self._stream.stop()
        self._stream.close()


class _View:
    """Читатель общего микрофона с интерфейсом RawInputStream."""

    def __init__(self, mic, pos):
        self.mic = mic
        self.pos = pos

    def __enter__(self):
        return self

    def __exit__(self, *a):
        global _last_pos, _last_at
        _last_pos, _last_at = self.pos, time.time()
        return False

    def read(self, n):
        data, self.pos = self.mic.read(self.pos, n)
        return data, False


def start_shared(device=None):
    global _shared
    if _shared is None:
        _shared = SharedMic(device=device)
    return _shared


def take_overflows():
    """Сколько раз микрофон переполнился с прошлого вызова (звук потерян)."""
    if _shared is None:
        return 0
    n, _shared.overflows = _shared.overflows, 0
    return n


def open_stream(rate, blocksize, device=None, resume=False):
    if _shared is not None and rate == _shared.rate and device == _shared.device:
        fresh = resume and _last_pos is not None and time.time() - _last_at < RESUME_SEC
        pos = _last_pos if fresh else _shared.total
        return _View(_shared, pos)
    return sd.RawInputStream(samplerate=rate, blocksize=blocksize, channels=1,
                             dtype="int16", device=device)
