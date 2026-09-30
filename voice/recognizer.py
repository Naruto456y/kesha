"""Распознавание речи через Google."""
import time
import speech_recognition as sr


class Recognizer:
    def __init__(self):
        self.rec = sr.Recognizer()
        self.rec.energy_threshold = 400
        self.rec.pause_threshold = 0.8
        self.rec.dynamic_energy_threshold = True
        self._last = 0
        self.adjust()

    def adjust(self):
        try:
            with sr.Microphone() as src:
                self.rec.adjust_for_ambient_noise(src, duration=2)
                self._last = time.time()
        except Exception as e:
            print("[recognizer]", e)

    def listen(self, timeout=5, phrase_limit=5):
        try:
            if time.time() - self._last > 1800:
                self.adjust()
            with sr.Microphone() as src:
                audio = self.rec.listen(src, timeout=timeout, phrase_time_limit=phrase_limit)
            return self.rec.recognize_google(audio, language="ru-RU").lower().strip()
        except Exception:
            return ""
