"""
Движки озвучки (волна 5: смена голоса).

    google  — gTTS, онлайн, умеет ru и en (голос по умолчанию)
    female  — Silero xenia, офлайн
    male    — Silero eugene, офлайн (по умолчанию)
    robot   — Silero eugene + кольцевая модуляция, офлайн
    sapi    — голос Windows (pyttsx3), офлайн, запасной вариант

Каждый движок: synth(text, lang) -> путь к аудиофайлу. Если движок упал,
speaker пробует следующий по списку engine_order().
"""

import os
import re
import sys
import tempfile
import threading
import time
import wave

import numpy as np

from config import SILERO_MODEL_PATH, SILERO_SPEAKERS, SILERO_SAMPLE_RATE, TTS_SLOW
from .text_norm import latin_to_ru, normalize_for_tts

VOICES = ("google", "female", "male", "robot")
GOOGLE_TIMEOUT = 4      # с; gTTS из России отвечает 7–10 с — дольше ждать незачем, есть SAPI


def _tmp(ext):
    return os.path.join(tempfile.gettempdir(), "kesha_%d_%d.%s" % (
        int(time.time() * 1000), threading.get_ident() % 10000, ext))


def _write_wav(path, samples, rate):
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def wav_length(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


# ---------- gTTS ----------
def synth_google(text, lang="ru"):
    from gtts import gTTS
    path = _tmp("mp3")
    gTTS(text=text, lang=lang, slow=TTS_SLOW, timeout=GOOGLE_TIMEOUT).save(path)
    return path


# ---------- Silero ----------
_silero = None
_silero_lock = threading.Lock()


def load_silero():
    """Загрузить модель (≈7 с первый раз). Потокобезопасно, грузится один раз."""
    global _silero
    with _silero_lock:
        if _silero is None:
            import torch
            if not SILERO_MODEL_PATH.exists():
                raise RuntimeError(f"нет модели Silero: {SILERO_MODEL_PATH}")
            model = torch.package.PackageImporter(str(SILERO_MODEL_PATH)).load_pickle(
                "tts_models", "model")
            model.to(torch.device("cpu"))
            _silero = model
        return _silero


def preload_silero():
    if "pytest" in sys.modules:       # тестам 12 с загрузки torch-модели ни к чему
        return
    threading.Thread(target=_safe_preload, daemon=True, name="silero-preload").start()


def _safe_preload():
    try:
        model = load_silero()
        with _silero_lock:      # первая фраза у torch ~1.5 с (прогрев) — тратим их при запуске
            model.apply_tts(text="Привет", speaker=SILERO_SPEAKERS["female"], sample_rate=SILERO_SAMPLE_RATE)
        print("[tts] Silero загружена и прогрета")
    except Exception as e:
        print(f"[tts] Silero недоступна: {e}")


def robotize(samples, rate):
    """Кольцевая модуляция + лёгкое «зерно» — голос робота."""
    t = np.arange(len(samples)) / rate
    carrier = np.sin(2 * np.pi * 55 * t)
    y = 0.75 * samples * carrier + 0.25 * samples
    y = np.round(y * 64) / 64            # понижаем разрядность
    peak = float(np.max(np.abs(y))) or 1.0
    return y / peak * 0.9


SILERO_MAX_CHARS = 800      # длиннее Silero падает — режем по предложениям


def _chunks(text, limit=SILERO_MAX_CHARS):
    parts, cur = [], ""
    for sent in re.split(r"(?<=[.!?…])\s+", text):
        if cur and len(cur) + len(sent) + 1 > limit:
            parts.append(cur)
            cur = ""
        cur = f"{cur} {sent}".strip()
        while len(cur) > limit:                 # одно огромное «предложение» без точек
            cut = cur.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            parts.append(cur[:cut])
            cur = cur[cut:].strip()
    if cur:
        parts.append(cur)
    return parts


def synth_silero(text, voice="female"):
    # латиницу не отдаём в gTTS (там другой голос) — читаем её по-русски
    clean = normalize_for_tts(latin_to_ru(text))
    if not re.search(r"[а-яА-ЯёЁ]", clean):
        raise ValueError("нечего озвучивать")
    model = load_silero()
    speaker = SILERO_SPEAKERS.get(voice, "xenia")
    pieces = []
    with _silero_lock:
        for part in _chunks(clean):
            pieces.append(model.apply_tts(text=part, speaker=speaker, sample_rate=SILERO_SAMPLE_RATE).numpy())
    samples = np.concatenate(pieces).astype(np.float32)
    if voice == "robot":
        samples = robotize(samples, SILERO_SAMPLE_RATE)
    path = _tmp("wav")
    _write_wav(path, samples, SILERO_SAMPLE_RATE)
    return path


# ---------- голос Windows ----------
def synth_sapi(text, lang="ru"):
    import pyttsx3
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    engine = pyttsx3.init()
    want = "ru" if lang == "ru" else "en"
    for v in engine.getProperty("voices"):
        langs = " ".join(str(x) for x in (getattr(v, "languages", None) or [])).lower()
        if want in langs or want in (v.id or "").lower():
            engine.setProperty("voice", v.id)
            break
    path = _tmp("wav")
    engine.save_to_file(text, path)
    engine.runAndWait()
    engine.stop()
    if not os.path.exists(path) or os.path.getsize(path) < 100:
        raise RuntimeError("SAPI не создал файл")
    return path


def engine_order(voice, lang):
    """Список (имя, функция) — в каком порядке пробовать движки."""
    if lang != "ru":
        return [("google", lambda t: synth_google(t, lang)), ("sapi", lambda t: synth_sapi(t, lang))]
    if voice in ("female", "male", "robot"):
        return [("silero", lambda t: synth_silero(t, voice)), ("google", synth_google),
                ("sapi", synth_sapi)]
    return [("google", synth_google), ("silero", lambda t: synth_silero(t, "female")),
            ("sapi", synth_sapi)]
