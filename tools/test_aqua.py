"""Живой тест Aqua STT: python tools/test_aqua.py [--bad-key] [--secs 5]
Записывает речь с микрофона, шлёт в Aqua, печатает текст и время ответа.
--bad-key подставляет неверный ключ: проверка перехода на локальный GigaAM."""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import sounddevice as sd

ap = argparse.ArgumentParser()
ap.add_argument("--secs", type=float, default=5)
ap.add_argument("--bad-key", action="store_true")
a = ap.parse_args()

import os
if a.bad_key:
    os.environ["AQUA_API_KEY"] = "bad-key-for-test"

import aqua_stt
from voice.gigaam_recognizer import GigaAMRecognizer

print(f"Говорите {a.secs:g} с (например: «вперёд», «назад», «включи музыку»)...")
audio = sd.rec(int(a.secs * 16000), samplerate=16000, channels=1, dtype="int16")
sd.wait()
pcm = audio.tobytes()
print(f"уровень: {np.abs(audio).max()} / 32767")

rec = aqua_stt.AquaRecognizer(GigaAMRecognizer())
text = rec.recognize(pcm)
print(f"[{rec.last_engine}] {rec.last_ms} мс -> {text!r}")
text2 = rec.recognize(pcm)  # второй вызов: после сбоя должен сразу идти в local
print(f"[{rec.last_engine}] {rec.last_ms} мс -> {text2!r}")
