"""Голосовой цикл Кеши: WakeWord -> VAD -> GigaAM -> handle_command -> TTS."""
import time

from core import handle_command
from config import WAKE_WORDS, MIC_ACTIVE_WINDOW
from state_manager import State, set_state
from .speaker import say, is_mic_blocked

WAKE_LISTEN_TIMEOUT = 6.0   # сколько ждём команду после wake word, сек


def _has_wake(t):
    return any(w in t for w in WAKE_WORDS)


def _clean(t):
    for w in WAKE_WORDS:
        t = t.replace(w, "")
    return t.strip()


class VoiceLoop:
    def __init__(self, rec, vad, ww):
        self.rec = rec
        self.vad = vad
        self.ww = ww   # None -> слово-активатор ищем голосом через GigaAM

    def _speak(self, text):
        set_state(State.SPEAKING, text=text)
        say(text)
        time.sleep(0.05)
        while is_mic_blocked():
            time.sleep(0.05)

    def _listen(self, max_wait, passive=False):
        """passive=True: ищем слово-активатор в потоке (wake word через GigaAM) —
        пока никто не заговорил, остаёмся в IDLE, а не в LISTENING."""
        if not passive:
            set_state(State.LISTENING)
        audio = self.vad.record(max_wait=max_wait, should_pause=is_mic_blocked)
        if not audio:
            return ""
        set_state(State.THINKING)
        text = self.rec.recognize(audio)
        print(f"[voice] услышал: {text!r}")
        return text

    def _process(self, cmd):
        set_state(State.THINKING, text=cmd)
        resp = handle_command(cmd, source="voice")
        if resp:
            self._speak(resp)

    def _active_window(self, first_wait):
        """Принимаем команды без wake word, пока пользователь не замолчит."""
        wait = first_wait
        while True:
            text = self._listen(wait)
            if not text:
                return
            cmd = _clean(text)
            if cmd:
                self._process(cmd)
            wait = MIC_ACTIVE_WINDOW

    def run(self):
        self._speak("Готов к работе.")
        while True:
            try:
                set_state(State.IDLE)
                if self.ww is not None:
                    if not self.ww.wait_for_wake(should_pause=is_mic_blocked):
                        continue
                    set_state(State.WAKE)
                    self._active_window(WAKE_LISTEN_TIMEOUT)
                else:
                    text = self._listen(None, passive=True)
                    if not text or not _has_wake(text):
                        continue
                    set_state(State.WAKE)
                    cmd = _clean(text)
                    if cmd:
                        self._process(cmd)
                        self._active_window(MIC_ACTIVE_WINDOW)
                    else:
                        self._active_window(WAKE_LISTEN_TIMEOUT)
            except Exception as e:
                print("[voice]", e)
                set_state(State.ERROR, error=str(e))
                time.sleep(1)


def _legacy_loop():
    """Старый цикл на Google-распознавателе — страховка, если новый стек не поднялся."""
    from .recognizer import Recognizer
    rec = Recognizer()
    say("Готов к работе.")
    while True:
        try:
            while True:
                if is_mic_blocked():
                    time.sleep(0.1)
                    continue
                t = rec.listen(timeout=10)
                if t and _has_wake(t):
                    break
            cmd = _clean(t)
            if cmd:
                r = handle_command(cmd, source="voice")
                if r:
                    say(r)
            start = time.time()
            while time.time() - start < MIC_ACTIVE_WINDOW:
                if is_mic_blocked():
                    time.sleep(0.1)
                    continue
                c = rec.listen(timeout=1)
                if not c:
                    time.sleep(0.05)
                    continue
                cc = _clean(c)
                if cc:
                    r = handle_command(cc, source="voice")
                    if r:
                        say(r)
                    start = time.time()
        except Exception as e:
            print("[voice]", e)
            time.sleep(1)


def start_voice_loop():
    try:
        from .gigaam_recognizer import GigaAMRecognizer
        from .vad_recorder import VADRecorder
        rec = GigaAMRecognizer()
        vad = VADRecorder()
    except Exception as e:
        print(f"[voice] новый стек недоступен ({e}), запускаю старый Google-распознаватель")
        set_state(State.ERROR, error=str(e))
        _legacy_loop()
        return

    ww = None
    try:
        from .wake_word import WakeWordDetector
        ww = WakeWordDetector()
        print("[voice] wake word: Porcupine ('computer')")
    except Exception as e:
        print(f"[voice] ВНИМАНИЕ: Porcupine недоступен ({e}). "
              f"Работаю без него: слово-активатор ({', '.join(WAKE_WORDS)}) ищу через GigaAM")

    VoiceLoop(rec, vad, ww).run()
