"""Озвучка ответов Кеши (gTTS + pygame)."""
import os, time, tempfile, threading
import pygame
from gtts import gTTS
from config import TTS_LANG, TTS_SLOW


class Speaker:
    def __init__(self):
        try:
            pygame.mixer.init()
        except Exception as e:
            print("[speaker] pygame init failed:", e)
        self.is_speaking = False
        self.mic_blocked_until = 0.0
        self._lock = threading.Lock()
        self._thread = None

    def say(self, text):
        if not text or not text.strip():
            return
        estimated = len(text) * 0.05 + 1.0
        with self._lock:
            self.mic_blocked_until = time.time() + estimated
            self.is_speaking = True
        try:
            fn = os.path.join(tempfile.gettempdir(), "kesha_%d.mp3" % int(time.time() * 1000))
            gTTS(text=text, lang=TTS_LANG, slow=TTS_SLOW).save(fn)
            if self._thread and self._thread.is_alive():
                pygame.mixer.music.stop()
                self._thread.join(timeout=0.5)
            pygame.mixer.music.load(fn)
            pygame.mixer.music.play()
            self._thread = threading.Thread(target=self._cleanup, args=(fn,), daemon=True)
            self._thread.start()
        except Exception as e:
            print("[speaker]", e)
            with self._lock:
                self.is_speaking = False
                self.mic_blocked_until = 0.0

    def _cleanup(self, fn):
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        with self._lock:
            self.is_speaking = False
            self.mic_blocked_until = time.time()
        try: os.remove(fn)
        except Exception: pass

    def is_mic_blocked(self):
        with self._lock:
            return time.time() < self.mic_blocked_until


speaker = Speaker()
say = speaker.say
is_speaking = lambda: speaker.is_speaking
is_mic_blocked = speaker.is_mic_blocked
