"""
Шумодав перед распознаванием: спектральное вычитание по самой записи.

Шум (вентилятор ноутбука, гул, шипение микрофона) ровный, а речь — нет. Для каждой
частоты берём её тихий уровень за всю запись (10-й перцентиль) — это и есть шум —
и ослабляем всё, что не выше него. Речь поверх шума остаётся.

Работает только на ровном шуме. Музыку, телевизор и чужие голоса не убирает:
для этого нужна нейросеть. Включается настройкой «denoise».
"""
import numpy as np

RATE = 16000
N_FFT = 512
HOP = 128
NOISE_PCT = 10          # тихий уровень частоты за запись = шум
OVERSUB = 1.5           # вычитаем шум с запасом
FLOOR = 0.12            # но не тише этой доли исходного: полная тишина звучит для STT неестественно
MIN_SEC = 0.5           # на коротком звуке шум не оценить


def denoise(audio: bytes) -> bytes:
    """PCM int16 mono 16 кГц -> то же, с приглушённым ровным шумом."""
    pcm = np.frombuffer(audio, dtype=np.int16)
    if len(pcm) < MIN_SEC * RATE:
        return audio
    x = pcm.astype(np.float32) / 32768.0
    win = np.hanning(N_FFT + 1)[:-1].astype(np.float32)
    pad = N_FFT
    xp = np.concatenate([np.zeros(pad, np.float32), x, np.zeros(pad, np.float32)])
    n = 1 + (len(xp) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    spec = np.fft.rfft(xp[idx] * win, axis=1)
    mag = np.abs(spec)
    noise = np.percentile(mag, NOISE_PCT, axis=0, keepdims=True)
    gain = np.maximum(1.0 - OVERSUB * noise / (mag + 1e-9), FLOOR)
    # сглаживаем по времени: резкие скачки усиления дают «булькающий» музыкальный шум
    k = np.array([0.25, 0.5, 0.25], dtype=np.float32)
    gain = np.apply_along_axis(lambda g: np.convolve(g, k, mode="same"), 0, gain)
    frames = np.fft.irfft(spec * gain, n=N_FFT, axis=1).astype(np.float32) * win
    out = np.zeros(len(xp), dtype=np.float32)
    norm = np.zeros(len(xp), dtype=np.float32)
    for i in range(n):
        out[i * HOP:i * HOP + N_FFT] += frames[i]
        norm[i * HOP:i * HOP + N_FFT] += win * win
    out = out / np.maximum(norm, 1e-6)
    y = out[pad:pad + len(x)]
    return (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
