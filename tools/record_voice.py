"""Запись с микрофона в WAV (16 кГц, моно) для проверки GigaAM.

python record_voice.py              # 5 секунд -> my_voice.wav
python record_voice.py 8 test.wav   # 8 секунд -> test.wav
python record_voice.py --devices    # список аудиоустройств
"""
import sys
import time

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000  # GigaAM работает с 16 кГц


def main() -> None:
    if "--devices" in sys.argv:
        print(sd.query_devices())
        return

    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    out = sys.argv[2] if len(sys.argv) > 2 else "my_voice.wav"

    if seconds > 25:
        print("⚠️ transcribe рассчитан примерно на 25 секунд, длиннее будет ошибка")

    for n in (3, 2, 1):
        print(f"⏳ Старт через {n}...")
        time.sleep(1)

    print(f"🔴 ГОВОРИ! Идёт запись {seconds:g} с")
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()

    peak = int(np.abs(audio).max())
    sf.write(out, audio, SAMPLE_RATE, subtype="PCM_16")
    print(f"✅ Сохранено: {out} (пик громкости {peak} из 32767)")

    if peak < 500:
        print("⚠️ Очень тихо. Проверь микрофон: python record_voice.py --devices")
    else:
        print(f"▶️ Дальше: python diag_gigaam.py {out}")


if __name__ == "__main__":
    main()
