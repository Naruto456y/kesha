"""Тест VAD: до 5 секунд записи, остановка по 0.8 с тишины."""
import sys
import time
from _common import load

mod = load("vad_recorder")
vad = mod.VADRecorder()
print(f"VAD: {'webrtcvad' if vad.vad is not None else 'энергетический (webrtcvad не установлен)'}")
print("Скажи короткую фразу и замолчи (жду речь до 5 сек)...")

t0 = time.time()
audio = vad.record(max_wait=5, max_seconds=5)
info = vad.last_info
dur = len(audio) / 2 / 16000
print(f"Длина записи: {dur:.2f} с | прошло времени: {time.time() - t0:.2f} с | остановка: {info['stopped_by']}")

if info["stopped_by"] == "silence":
    print("✅ ТЕСТ VAD ПРОЙДЕН: запись обрезалась по тишине")
    sys.exit(0)
if info["stopped_by"] == "no_speech":
    print("❌ Речь не обнаружена (проверь микрофон / доступ к нему в Windows)")
else:
    print("⚠️ Запись упёрлась в лимит, а не в тишину")
sys.exit(1)
