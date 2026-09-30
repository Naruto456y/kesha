"""Голосовой цикл Кеши."""
import time
from core import handle_command
from config import WAKE_WORDS, MIC_ACTIVE_WINDOW
from .speaker import say, is_mic_blocked
from .recognizer import Recognizer


def _has_wake(t):
    return any(w in t for w in WAKE_WORDS)


def _clean(t):
    for w in WAKE_WORDS:
        t = t.replace(w, "")
    return t.strip()


def start_voice_loop():
    rec = Recognizer()
    say("Готов к работе.")
    while True:
        try:
            while True:
                if is_mic_blocked():
                    time.sleep(0.1); continue
                t = rec.listen(timeout=10)
                if t and _has_wake(t):
                    break
            cmd = _clean(t)
            if cmd:
                r = handle_command(cmd, source="voice")
                if r: say(r)
            start = time.time()
            while time.time() - start < MIC_ACTIVE_WINDOW:
                if is_mic_blocked():
                    time.sleep(0.1); continue
                c = rec.listen(timeout=1)
                if not c:
                    time.sleep(0.05); continue
                cc = _clean(c)
                if cc:
                    r = handle_command(cc, source="voice")
                    if r: say(r)
                    start = time.time()
        except Exception as e:
            print("[voice]", e)
            time.sleep(1)
