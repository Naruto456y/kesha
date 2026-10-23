"""
Распознавание речи GigaAM v3 через onnx-asr (без PyTorch / TensorFlow).
recognize(audio_bytes) принимает сырой PCM int16, mono, 16 kHz.
Модель лежит в models/gigaam/ (кэш HuggingFace внутри проекта).
"""
import os
import re
import threading
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models" / "gigaam"
MARKER = MODEL_DIR / ".downloaded"
MODEL_NAME = "gigaam-v3-e2e-ctc"   # e2e: пунктуация и числа цифрами ("громкость 50")
QUANTIZATION = "int8"              # ~225 МБ
SAMPLE_RATE = 16000

os.environ.setdefault("HF_HUB_CACHE", str(MODEL_DIR))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

_PUNCT = re.compile(r"[^\w\s-]+", re.UNICODE)
_LONE_HYPHEN = re.compile(r"(?<!\w)-|-(?!\w)")


def normalize(text):
    """Нижний регистр, без пунктуации — под паттерны commands.py."""
    text = _PUNCT.sub(" ", (text or "").lower())
    text = _LONE_HYPHEN.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _local_snapshot():
    snaps = [p for p in MODEL_DIR.glob("models--*gigaam*/snapshots/*") if p.is_dir()]
    snaps.sort(key=lambda p: p.stat().st_mtime)
    return snaps[-1] if snaps else None


class GigaAMRecognizer:
    def __init__(self, model_name=MODEL_NAME, quantization=QUANTIZATION):
        import onnx_asr
        attempts = []
        snap = _local_snapshot()
        if snap is not None:
            attempts.append(dict(path=str(snap), quantization=quantization))
        attempts.append(dict(quantization=quantization))
        attempts.append(dict())
        last = None
        self._model = None
        for kw in attempts:
            try:
                self._model = onnx_asr.load_model(model_name, **kw)
                break
            except Exception as e:
                last = e
                print(f"[gigaam] загрузка {kw} не удалась: {e}")
        if self._model is None:
            raise RuntimeError(f"GigaAM не загрузился: {last}")
        self._lock = threading.Lock()

    def recognize(self, audio_bytes, sample_rate=SAMPLE_RATE, normalize_text=True):
        """audio_bytes: PCM int16 mono. Возвращает текст (пустую строку, если речи нет)."""
        if not audio_bytes or len(audio_bytes) < int(sample_rate * 2 * 0.2):
            return ""
        pcm = np.frombuffer(audio_bytes, dtype=np.int16)
        wav = pcm.astype(np.float32) / 32768.0
        with self._lock:
            text = self._model.recognize(wav, sample_rate=sample_rate)
        text = str(text or "")
        return normalize(text) if normalize_text else text.strip()

    def recognize_file(self, path, normalize_text=True):
        with self._lock:
            text = str(self._model.recognize(str(path)) or "")
        return normalize(text) if normalize_text else text.strip()
