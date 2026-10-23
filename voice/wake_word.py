"""Wake word на Porcupine. Пока слово 'computer'; 'Кешу' потом заберёт GigaAM."""
import os
import struct
import time
from pathlib import Path

import sounddevice as sd

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

ENV_KEY = "PICOVOICE_ACCESS_KEY"
DEFAULT_KEYWORD = "computer"


class WakeWordDetector:
    def __init__(self, keyword=DEFAULT_KEYWORD, keyword_path=None, access_key=None,
                 sensitivity=0.6, device=None):
        import pvporcupine
        key = (access_key or os.environ.get(ENV_KEY, "")).strip()
        if not key:
            raise RuntimeError(f"нет {ENV_KEY} в .env (ключ: console.picovoice.ai)")
        kwargs = dict(access_key=key, sensitivities=[sensitivity])
        if keyword_path:
            kwargs["keyword_paths"] = [keyword_path]
        else:
            kwargs["keywords"] = [keyword]
        self._porcupine = pvporcupine.create(**kwargs)
        self.frame_length = self._porcupine.frame_length   # 512
        self.sample_rate = self._porcupine.sample_rate     # 16000
        self.device = device
        self._stop = False

    def stop(self):
        self._stop = True

    def wait_for_wake(self, timeout=None, should_pause=None):
        """Блокируется до детекции. True — услышал, False — таймаут/stop().
        should_pause() -> True: кадры выбрасываются (Кеша сейчас говорит)."""
        self._stop = False
        deadline = None if timeout is None else time.time() + timeout
        fmt = "h" * self.frame_length
        with sd.RawInputStream(samplerate=self.sample_rate, blocksize=self.frame_length,
                               device=self.device, channels=1, dtype="int16") as stream:
            while not self._stop:
                if deadline is not None and time.time() > deadline:
                    return False
                data, _overflow = stream.read(self.frame_length)
                if should_pause is not None and should_pause():
                    continue
                pcm = struct.unpack_from(fmt, bytes(data))
                if self._porcupine.process(pcm) >= 0:
                    return True
        return False

    def close(self):
        try:
            self._porcupine.delete()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
