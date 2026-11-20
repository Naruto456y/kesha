"""Помогает ли шумодав распознаванию: python tools/denoise_test.py

Берёт записи команд из базы голоса (data/voice_db) и data/my_voice.wav, подмешивает шум
разной силы и сравнивает, что распознаёт GigaAM без шумодава и с ним.
Число — похожесть на текст чистой записи, 100 = слово в слово."""
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rapidfuzz import fuzz  # noqa: E402

from voice import voicedb  # noqa: E402
from voice.denoise import denoise  # noqa: E402
from voice.gigaam_recognizer import GigaAMRecognizer  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def read(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)


def noises(n, rng):
    white = rng.normal(0, 1, n)
    pink = np.cumsum(white)
    pink -= np.convolve(pink, np.ones(400) / 400, mode="same")          # без медленного дрейфа
    t = np.arange(n) / 16000
    hum = np.sin(2 * np.pi * 120 * t) + 0.5 * np.sin(2 * np.pi * 240 * t) + 0.3 * white   # вентилятор
    return {"шипение": white, "гул": pink, "вентилятор": hum}


def mix(clean, noise, snr_db):
    p_s = np.mean(clean ** 2) + 1e-9
    p_n = np.mean(noise ** 2) + 1e-9
    y = clean + noise * np.sqrt(p_s / p_n / 10 ** (snr_db / 10))
    return np.clip(y, -32768, 32767).astype(np.int16).tobytes()


def main():
    clips = [read(r[2]) for r in voicedb.rows("command", limit=30)]
    extra = ROOT / "data" / "my_voice.wav"
    if extra.exists():
        clips.append(read(extra))
    if not clips:
        sys.exit("Записей нет: поговори с Кешей, база голоса наполнится сама.")
    rec = GigaAMRecognizer()
    rng = np.random.default_rng(0)
    refs = [rec.recognize(c.astype(np.int16).tobytes()) for c in clips]
    pairs = [(c, r) for c, r in zip(clips, refs) if r]
    print(f"записей: {len(pairs)}\n{'шум':12}{'сигнал/шум':>11}{'без шумодава':>14}{'с шумодавом':>13}")
    total = [0.0, 0.0, 0]
    for snr in (15, 10, 5, 0):
        for name in ("шипение", "гул", "вентилятор"):
            raw = den = 0.0
            for clean, ref in pairs:
                noisy = mix(clean, noises(len(clean), rng)[name], snr)
                raw += fuzz.ratio(ref, rec.recognize(noisy))
                den += fuzz.ratio(ref, rec.recognize(denoise(noisy)))
            raw, den = raw / len(pairs), den / len(pairs)
            total = [total[0] + raw, total[1] + den, total[2] + 1]
            print(f"{name:12}{snr:>8} дБ{raw:>14.0f}{den:>13.0f}")
    clean_den = np.mean([fuzz.ratio(r, rec.recognize(denoise(c.astype(np.int16).tobytes()))) for c, r in pairs])
    print(f"\nчистая запись через шумодав: {clean_den:.0f} (100 = шумодав ничего не портит)")
    print(f"в среднем: без шумодава {total[0] / total[2]:.0f}, с шумодавом {total[1] / total[2]:.0f}")


if __name__ == "__main__":
    main()
