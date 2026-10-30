"""
Звуковые эффекты (волна 3): короткий «пик» при активации, «буп» при ошибке,
и звонок будильника. Тоны генерируются один раз в data/sounds/*.wav.
Выключаются настройкой «sounds» (будильник звонит всегда).
"""

import threading
import time
import wave

import numpy as np
import pygame

import settings
from config import DATA_DIR, ALARM_SOUND, ALARM_MAX_SEC

SOUNDS_DIR = DATA_DIR / "sounds"
RATE = 44100

# имя -> [(частота Гц, длительность с), ...]
TONES = {
    "wake":  [(660, 0.07), (990, 0.09)],     # «пик-пик» вверх (запасной, если «бульк» выключен)
    "done":  [(880, 0.06)],                  # короткий «тик» — принято
    "error": [(420, 0.12), (300, 0.18)],     # «буп-буп» вниз — не вышло
}

# «бульк» капли: тон быстро скользит вверх и затухает — мягче, чем «пик-пик»
BULK = {"wake": (380, 1150, 0.11)}           # (от Гц, до Гц, длительность с)

_cache = {}
_alarm = {"sound": None, "timer": None}
_alarm_lock = threading.Lock()


def _tone(freq, dur):
    t = np.arange(int(RATE * dur)) / RATE
    wave_ = np.sin(2 * np.pi * freq * t)
    fade = np.minimum(1.0, np.minimum(t, dur - t) / 0.012)   # без щелчков
    return wave_ * fade * 0.35


def _bulk(f0, f1, dur):
    t = np.arange(int(RATE * dur)) / RATE
    freq = f0 + (f1 - f0) * (t / dur) ** 0.6               # скольжение вверх
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    env = np.minimum(1.0, t / 0.004) * np.exp(-t / (dur / 3.5))
    return np.sin(phase) * env * 0.3


def sound_path(name):
    path = SOUNDS_DIR / (f"{name}_bulk.wav" if name in BULK else f"{name}.wav")
    if not path.exists():
        SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
        if name in BULK:
            parts = [_bulk(*BULK[name])]
        else:
            parts = []
            for freq, dur in TONES[name]:
                parts.append(_tone(freq, dur))
                parts.append(np.zeros(int(RATE * 0.025)))
        pcm = (np.concatenate(parts) * 32767).astype(np.int16)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm.tobytes())
    return path


def duration(name):
    if name in BULK:
        return BULK[name][2]
    return sum(d + 0.025 for _, d in TONES[name])


def _mixer():
    if not pygame.mixer.get_init():
        pygame.mixer.init()


def play(name):
    """Сыграть эффект, не блокируя поток. Микрофон закрываем на время звука."""
    if not settings.get("sounds"):
        return
    try:
        _mixer()
        snd = _cache.get(name)
        if snd is None:
            snd = _cache[name] = pygame.mixer.Sound(str(sound_path(name)))
        snd.play()
        try:
            from .speaker import speaker
            speaker.block_mic(duration(name) + 0.15)
        except Exception:
            pass
    except Exception as e:
        print(f"[sfx] {name}: {e}")


# ---------- будильник ----------
def alarm_start(max_sec=ALARM_MAX_SEC):
    with _alarm_lock:
        if _alarm["sound"] is not None:
            return
        try:
            _mixer()
            snd = pygame.mixer.Sound(str(ALARM_SOUND))
        except Exception as e:
            print(f"[sfx] будильник: {e}")
            return
        snd.play(loops=-1)
        _alarm["sound"] = snd
        timer = threading.Timer(max_sec, alarm_stop)
        timer.daemon = True
        timer.start()
        _alarm["timer"] = timer


def alarm_stop() -> bool:
    """True — будильник звенел и выключен."""
    with _alarm_lock:
        snd, timer = _alarm["sound"], _alarm["timer"]
        _alarm["sound"] = _alarm["timer"] = None
    if timer is not None:
        timer.cancel()
    if snd is None:
        return False
    try:
        snd.fadeout(300)
    except Exception:
        pass
    return True


def is_ringing() -> bool:
    return _alarm["sound"] is not None


def wait_quiet(timeout=1.0):
    end = time.time() + timeout
    while pygame.mixer.get_init() and pygame.mixer.get_busy() and time.time() < end:
        time.sleep(0.02)
