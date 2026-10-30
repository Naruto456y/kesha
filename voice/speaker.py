"""
Озвучка ответов Кеши (pygame). Движок выбирается настройкой «voice»
(google / female / male / robot), язык — настройкой «language».
Тихий режим (settings «silent») — не говорим вслух, ответ остаётся текстом.
Длительность mp3 — точная, через mutagen; wav — по заголовку.
"""
import os, re, time, threading
import pygame

import settings
from . import tts_engines

try:
    from mutagen.mp3 import MP3
except Exception as _e:
    print("[speaker] mutagen недоступен, длительность считаю по длине текста:", _e)
    MP3 = None

# смайлики и пиктограммы не читаем вслух
_EMOJI_RE = re.compile("[🀀-🫿☀-➿⬀-⯿️‍]+")

TAIL_SEC = 0.4        # запас на эхо после конца речи
GEN_GUARD_SEC = 20.0  # пока движок генерирует аудио, микрофон закрыт


def _audio_length(path, text):
    try:
        if path.endswith(".wav"):
            return tts_engines.wav_length(path)
        if MP3 is not None:
            return float(MP3(path).info.length)
    except Exception as e:
        print("[speaker] длительность:", e)
    return len(text) * 0.05 + 1.0   # запасная формула


def _remove(path):
    try:
        os.remove(path)
    except Exception:
        pass


def init_mixer():
    if not pygame.mixer.get_init():
        pygame.mixer.init()


class Speaker:
    def __init__(self):
        try:
            init_mixer()
        except Exception as e:
            print("[speaker] pygame init failed:", e)
        self.is_speaking = False
        self.mic_blocked_until = 0.0
        self.last_engine = None
        self._lock = threading.Lock()
        self._gen = 0
        self._on_setting("voice", settings.get("voice"))
        settings.subscribe(self._on_setting)

    def _on_setting(self, key, value):
        if key == "voice" and value in ("female", "male", "robot"):
            tts_engines.preload_silero()

    def _synthesize(self, text):
        """-> путь к файлу. Перебираем движки, пока какой-нибудь не сработает."""
        order = tts_engines.engine_order(settings.get("voice"), settings.get("language"))
        errors = []
        for name, synth in order:
            try:
                path = synth(text)
                self.last_engine = name
                return path
            except Exception as e:
                errors.append(f"{name}: {e}")
        raise RuntimeError("ни один движок не сработал — " + "; ".join(errors))

    def say(self, text, force=False):
        """force=True — говорить даже в тихом режиме (например, /say из Telegram)."""
        text = _EMOJI_RE.sub("", text or "").strip()
        if not text:
            return
        if settings.get("silent") and not force:
            return
        with self._lock:
            self._gen += 1
            gen = self._gen
            self.is_speaking = True
            self.mic_blocked_until = time.time() + GEN_GUARD_SEC
        fn = None
        try:
            fn = self._synthesize(text)
            length = _audio_length(fn, text)
            with self._lock:
                if gen != self._gen:   # пока генерировали, пришла более новая фраза
                    _remove(fn)
                    return
                self.mic_blocked_until = time.time() + length + TAIL_SEC
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.music.load(fn)
            pygame.mixer.music.play()
            threading.Thread(target=self._cleanup, args=(fn, gen), daemon=True).start()
        except Exception as e:
            print("[speaker]", e)
            if fn:
                _remove(fn)
            with self._lock:
                if gen == self._gen:
                    self.is_speaking = False
                    self.mic_blocked_until = 0.0

    def _cleanup(self, fn, gen):
        time.sleep(0.2)
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        with self._lock:
            latest = (gen == self._gen)
            if latest:
                self.is_speaking = False
                self.mic_blocked_until = time.time() + 0.3
        if latest:
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
        _remove(fn)

    def block_mic(self, seconds):
        """Закрыть микрофон на seconds (пока играет звуковой эффект)."""
        with self._lock:
            self.mic_blocked_until = max(self.mic_blocked_until, time.time() + seconds)

    def is_mic_blocked(self):
        with self._lock:
            return time.time() < self.mic_blocked_until


speaker = Speaker()
say = speaker.say
is_speaking = lambda: speaker.is_speaking
is_mic_blocked = speaker.is_mic_blocked
