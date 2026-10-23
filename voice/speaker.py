"""Озвучка ответов Кеши (gTTS + pygame). Длительность mp3 — точная, через mutagen."""
import os, re, time, tempfile, threading
import pygame
from gtts import gTTS
from config import TTS_LANG, TTS_SLOW

try:
    from mutagen.mp3 import MP3
except Exception as _e:
    print("[speaker] mutagen недоступен, длительность считаю по длине текста:", _e)
    MP3 = None

# смайлики и пиктограммы не читаем вслух
_EMOJI_RE = re.compile("[🀀-🫿☀-➿⬀-⯿️‍]+")

TAIL_SEC = 0.4        # запас на эхо после конца речи
GEN_GUARD_SEC = 20.0  # пока gTTS генерирует mp3, микрофон закрыт


def _mp3_length(path, text):
    if MP3 is not None:
        try:
            return float(MP3(path).info.length)
        except Exception as e:
            print("[speaker] mutagen:", e)
    return len(text) * 0.05 + 1.0   # запасная формула


def _remove(path):
    try:
        os.remove(path)
    except Exception:
        pass


class Speaker:
    def __init__(self):
        try:
            pygame.mixer.init()
        except Exception as e:
            print("[speaker] pygame init failed:", e)
        self.is_speaking = False
        self.mic_blocked_until = 0.0
        self._lock = threading.Lock()
        self._gen = 0

    def say(self, text):
        text = _EMOJI_RE.sub("", text or "").strip()
        if not text:
            return
        with self._lock:
            self._gen += 1
            gen = self._gen
            self.is_speaking = True
            self.mic_blocked_until = time.time() + GEN_GUARD_SEC
        fn = os.path.join(tempfile.gettempdir(), "kesha_%d.mp3" % int(time.time() * 1000))
        try:
            gTTS(text=text, lang=TTS_LANG, slow=TTS_SLOW).save(fn)
            length = _mp3_length(fn, text)
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

    def is_mic_blocked(self):
        with self._lock:
            return time.time() < self.mic_blocked_until


speaker = Speaker()
say = speaker.say
is_speaking = lambda: speaker.is_speaking
is_mic_blocked = speaker.is_mic_blocked
