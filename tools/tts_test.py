"""Проверка синтеза речи Silero TTS (v5_6_ru, работает на CPU).

python tts_test.py                          # фраза по умолчанию, голос xenia
python tts_test.py "Привет, я Кеша" baya    # свой текст и голос
Голоса: aidar, baya, kseniya, xenia, eugene
"""
import sys
import time
from pathlib import Path

import sounddevice as sd
import soundfile as sf
import torch

MODEL_ID = "v5_6_ru"
MODEL_URL = f"https://models.silero.ai/models/tts/ru/{MODEL_ID}.pt"
MODEL_PATH = Path(__file__).with_name(f"silero_{MODEL_ID}.pt")
SAMPLE_RATE = 48000
SPEAKERS = ["aidar", "baya", "kseniya", "xenia", "eugene"]
DEFAULT_TEXT = "Привет! Меня зовут Кеша. Я твой голосовой ассистент."
OUT_FILE = "tts_out.wav"


def load_model():
    if not MODEL_PATH.exists():
        print(f"⏳ Скачиваю модель {MODEL_ID} (один раз)...")
        torch.hub.download_url_to_file(MODEL_URL, str(MODEL_PATH))
    model = torch.package.PackageImporter(str(MODEL_PATH)).load_pickle(
        "tts_models", "model"
    )
    model.to(torch.device("cpu"))
    return model


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEXT
    speaker = sys.argv[2] if len(sys.argv) > 2 else "xenia"
    if speaker not in SPEAKERS:
        sys.exit(f"❌ Нет голоса '{speaker}'. Доступны: {', '.join(SPEAKERS)}")

    t0 = time.perf_counter()
    model = load_model()
    print(f"✅ Модель загружена за {time.perf_counter() - t0:.1f} с")

    t0 = time.perf_counter()
    audio = model.apply_tts(text=text, speaker=speaker, sample_rate=SAMPLE_RATE)
    elapsed = time.perf_counter() - t0

    wav = audio.numpy()
    duration = len(wav) / SAMPLE_RATE
    sf.write(OUT_FILE, wav, SAMPLE_RATE)
    print(f"⏱️  Синтез: {elapsed:.2f} с на {duration:.1f} с речи")
    print(f"💾 Сохранено: {OUT_FILE}")

    print("🔊 Играю...")
    sd.play(wav, SAMPLE_RATE)
    sd.wait()


if __name__ == "__main__":
    main()
