"""Скачать GigaAM v3 в models/gigaam/ (разово) и проверить, что модель грузится."""
import time
from _common import load

mod = load("gigaam_recognizer")
print(f"Каталог модели: {mod.MODEL_DIR}")
t0 = time.time()
mod.GigaAMRecognizer()
mod.MODEL_DIR.mkdir(parents=True, exist_ok=True)
mod.MARKER.write_text("ok", encoding="utf-8")
print(f"Модель на месте и загружается ({time.time() - t0:.1f} с)")
