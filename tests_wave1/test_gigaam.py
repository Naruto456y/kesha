"""Тест GigaAM: gTTS 'включи свет' -> mp3 -> PCM16 16 kHz -> GigaAMRecognizer."""
import sys
import tempfile
import time
from pathlib import Path
from _common import load

import numpy as np
import soundfile as sf
from gtts import gTTS

mod = load("gigaam_recognizer")

mp3 = Path(tempfile.gettempdir()) / "kesha_w1_test.mp3"
gTTS("включи свет", lang="ru").save(str(mp3))
data, sr = sf.read(str(mp3), dtype="float32")
if data.ndim > 1:
    data = data.mean(axis=1)
if sr != 16000:
    n = int(len(data) * 16000 / sr)
    data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data).astype(np.float32)
pcm = (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
print(f"Тестовая фраза: {len(data) / 16000:.2f} с аудио")

t0 = time.time()
rec = mod.GigaAMRecognizer()
print(f"Модель загружена за {time.time() - t0:.1f} с")

t0 = time.time()
text = rec.recognize(pcm)
print(f"Распознано за {time.time() - t0:.2f} с: {text!r}")

try:
    mp3.unlink()
except Exception:
    pass

ok = "свет" in text
print("✅ ТЕСТ GigaAM ПРОЙДЕН" if ok else "❌ ТЕСТ GigaAM НЕ ПРОЙДЕН (ждал 'включи свет')")
sys.exit(0 if ok else 1)
