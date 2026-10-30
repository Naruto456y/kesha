"""Wake word на Porcupine.

По умолчанию — встроенное слово 'computer'. Своё слово «Кеша»:
  1) на console.picovoice.ai обучи ключевое слово (язык Russian) -> скачай .ppn;
  2) положи его в models/porcupine/ (или укажи PICOVOICE_KEYWORD_PATH в .env);
  3) для русского слова нужна модель porcupine_params_ru.pv — тоже в models/porcupine/
     (или PICOVOICE_MODEL_PATH). Её берут из репозитория Picovoice/porcupine (lib/common).
Без PICOVOICE_ACCESS_KEY Porcupine не стартует — тогда слово ищет GigaAM.
"""
import os
import struct
import time
from pathlib import Path

import sounddevice as sd

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

ENV_KEY = "PICOVOICE_ACCESS_KEY"
DEFAULT_KEYWORD = "computer"
PORCUPINE_DIR = ROOT / "models" / "porcupine"


def find_custom_files():
    """-> (путь .ppn или None, путь .pv или None) из .env или models/porcupine/."""
    kw = os.environ.get("PICOVOICE_KEYWORD_PATH", "").strip() or None
    model = os.environ.get("PICOVOICE_MODEL_PATH", "").strip() or None
    if PORCUPINE_DIR.exists():
        if kw is None:
            ppn = sorted(PORCUPINE_DIR.glob("*.ppn"))
            kw = str(ppn[0]) if ppn else None
        if model is None:
            pv = sorted(PORCUPINE_DIR.glob("*.pv"))
            model = str(pv[0]) if pv else None
    return kw, model


class WakeWordDetector:
    def __init__(self, keyword=DEFAULT_KEYWORD, keyword_path=None, access_key=None,
                 sensitivity=0.6, device=None, model_path=None):
        import pvporcupine
        key = (access_key or os.environ.get(ENV_KEY, "")).strip()
        if not key:
            raise RuntimeError(f"нет {ENV_KEY} в .env (ключ: console.picovoice.ai)")
        if keyword_path is None and model_path is None:
            keyword_path, model_path = find_custom_files()
        kwargs = dict(access_key=key, sensitivities=[sensitivity])
        if keyword_path:
            kwargs["keyword_paths"] = [keyword_path]
            if model_path:
                kwargs["model_path"] = model_path
            self.label = Path(keyword_path).stem
        else:
            kwargs["keywords"] = [keyword]
            self.label = keyword
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
