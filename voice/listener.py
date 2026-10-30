"""Голосовой цикл Кеши: WakeWord -> VAD -> GigaAM -> handle_command -> TTS.

Активация: слово «Кеша» (Porcupine или GigaAM), горячая клавиша (HOTKEY,
по умолчанию Ctrl+Space), кнопка «СЛУШАТЬ» в окне или клик по значку — arm().
"""
import queue
import threading
import time

import persona
import klog
from core import handle_command, quick_control
from config import WAKE_WORDS, MIC_ACTIVE_WINDOW, HOTKEY, STT_ENGINE
from state_manager import State, set_state
from .speaker import say, is_mic_blocked
from . import sfx
from . import duck
from .loudness import ShoutDetector, speech_db as speech_level
from wake_text import addressed_to_other, near_kesha, has_wake as _has_wake, strip_wake as _clean, from_last_wake as _from_last_wake

WAKE_LISTEN_TIMEOUT = 6.0   # сколько ждём команду после wake word, сек
ARM_TIMEOUT = 8.0           # после горячей клавиши — сколько ждём начала речи
SHOUT_REPLY = "Не ори на меня, я и так прекрасно слышу."
# без «Кеша» длинная фраза — это фон (видео, разговор), а не команда:
# «экономить на том сверни вниз… я перестал платить…» сворачивало окно
BACKGROUND_MAX_WORDS = 6
_ERROR_PREFIXES = ("Не понял", "Ошибка", "Не удалось", "Не нашёл", "Не буду")

_current = None             # работающий VoiceLoop — для arm() из UI
_stt_lock = threading.Lock()  # GigaAM зовут поток wake word, быстрые команды и цикл — по очереди


def is_error_reply(resp):
    return bool(resp) and resp.startswith(_ERROR_PREFIXES)


class VoiceLoop:
    def __init__(self, rec, vad, ww):
        self.rec = rec
        self.vad = vad
        self.ww = ww   # None -> слово-активатор ищем голосом через GigaAM
        self.shout = ShoutDetector()
        self._armed_at = None
        self._arm_lock = threading.Lock()
        self._last_audio = b""

    # ---------- активация без слова ----------
    def arm(self):
        """Горячая клавиша / кнопка: слушать следующую фразу без «Кеша».
        Если звенит будильник — сначала выключаем его."""
        if sfx.alarm_stop():
            return
        stamp = time.time()
        with self._arm_lock:
            self._armed_at = stamp
        duck.duck()
        sfx.play("wake")
        set_state(State.LISTENING, via="hotkey")
        if self.ww is not None:
            self.ww.stop()
        self._schedule_expiry(stamp, ARM_TIMEOUT)

    def _schedule_expiry(self, stamp, delay):
        timer = threading.Timer(delay, self._expire_arm, args=(stamp,))
        timer.daemon = True
        timer.start()

    def _expire_arm(self, stamp):
        """Нажали клавишу и молчат — через ARM_TIMEOUT реактор снова «ждёт».
        Если фраза уже пишется — не обрываем, проверим позже."""
        if getattr(self.vad, "speech_active", False):
            self._schedule_expiry(stamp, 1.0)
            return
        with self._arm_lock:
            if self._armed_at != stamp:
                return
            self._armed_at = None
        duck.restore()
        set_state(State.IDLE)

    def _take_arm(self, speech_started_at=None):
        """Была ли активация клавишей (и речь началась вовремя). Сбрасывает флаг."""
        with self._arm_lock:
            armed, self._armed_at = self._armed_at, None
        if armed is None:
            return False
        when = speech_started_at if speech_started_at is not None else time.time()
        return when - armed <= ARM_TIMEOUT

    # ---------- речь ----------
    def _speak(self, text):
        set_state(State.SPEAKING, text=text)
        say(text)
        time.sleep(0.05)
        while is_mic_blocked():
            time.sleep(0.05)

    def _recognize(self, audio, local=False):
        """local=True — поиск слова-активатора: только офлайн, в Aqua уходит запись после активации."""
        if local and hasattr(self.rec, "local"):
            with _stt_lock:
                return self.rec.local.recognize(audio)
        return self.rec.recognize(audio)

    def _listen(self, max_wait, passive=False, start_audio=None):
        """passive=True: ищем слово-активатор в потоке (wake word через GigaAM) —
        пока никто не заговорил, остаёмся в IDLE, а не в LISTENING.
        start_audio — звук с «Кеша» из детектора: запись продолжает его."""
        if not passive:
            set_state(State.LISTENING)
        if start_audio:
            audio = self.vad.record(max_wait=max_wait, should_pause=is_mic_blocked, start_audio=start_audio)
        else:
            audio = self.vad.record(max_wait=max_wait, should_pause=is_mic_blocked)
        self._last_audio = audio or b""
        if not audio:
            return ""
        if (getattr(self.vad, "last_info", None) or {}).get("stopped_by") == "max":
            # 15 секунд без паузы — играет видео/ТВ. Не выбрасываем запись целиком:
            # пользователь мог сказать «Кеша, ...» поверх фона. Слушаем только если
            # в ней есть настоящее слово-активатор, и берём текст с него.
            set_state(State.THINKING)
            text = _from_last_wake(self._recognize(audio, local=True))
            if not text:
                klog.phrase("HEARD", "voice", "(фон)", "запись без паузы 15 с, слова «Кеша» нет")
                set_state(State.IDLE)
                return ""
            print(f"[voice] поверх фона услышал: {text!r}")
            klog.phrase("HEARD", "voice", text, "поверх фона, wake=да")
            return text
        set_state(State.THINKING)
        text = self._recognize(audio, local=passive)
        print(f"[voice] услышал: {text!r}")
        info = getattr(self.vad, "last_info", None) or {}
        klog.phrase("HEARD", "voice", text or "(пусто)",
                    f"{info.get('duration_sec', 0):.1f} с, wake={'да' if _has_wake(text) else 'нет'}"
                    f"{', ' + str(round(speech_level(audio), 1)) + ' dB' if audio else ''}")
        return text

    def _process(self, cmd, ai=True):
        """ai=False — фраза без «Кеша» в активном окне: только локальные команды."""
        set_state(State.THINKING, text=cmd)
        shouting = bool(self._last_audio) and self.shout.check(self._last_audio)
        resp = handle_command(cmd, source="voice", ai=ai)
        if not resp and not ai:
            set_state(State.LISTENING)
            return
        if is_error_reply(resp):
            sfx.play("error")
            sfx.wait_quiet(0.6)
        if shouting:
            resp = f"{SHOUT_REPLY} {resp}" if resp else SHOUT_REPLY
        if resp:
            self._speak(resp)

    def _active_window(self, first_wait, first_ai=True, start_audio=None):
        """Принимаем команды без wake word, пока пользователь не замолчит.
        first_ai — первая фраза сразу после «Кеша»/клавиши: это и есть команда, GigaChat можно.
        Дальше без «Кеша» — только точные/похожие команды: фоновая речь (ТВ, видео)
        не должна через GigaChat превращаться в действия."""
        wait, ai = first_wait, first_ai
        while True:
            if not ai:
                duck.restore()    # команда выполнена — 10 с ожидания следующей идут с обычной громкостью
            text = self._listen(wait, start_audio=start_audio)
            if not text:
                return
            if start_audio:
                # в записи есть и речь до «Кеша» — берём с последнего слова-активатора
                start_audio = None
                cmd = _clean(_from_last_wake(text) or text)
                if not cmd:
                    continue      # сказали только «Кеша» и замолчали — ждём команду как обычно
            else:
                cmd = _clean(text)
            woke = ai or _has_wake(text) or self._take_arm()
            if addressed_to_other(cmd):
                klog.phrase("IGNORED", "voice", cmd, "это Алисе (или другому помощнику), не Кеше")
            elif cmd and not woke and len(cmd.split()) > BACKGROUND_MAX_WORDS:
                klog.phrase("IGNORED", "voice", cmd, f"без «Кеша» и длиннее {BACKGROUND_MAX_WORDS} слов — фон")
            elif cmd:
                self._process(cmd, ai=woke)
            wait, ai = MIC_ACTIVE_WINDOW, False

    def _quick(self, text):
        """«громче», «пауза», «скролл вниз» без «Кеша» — молча делаем, отвечаем только ошибкой."""
        if addressed_to_other(text):
            return None          # «Алиса, громче» — громкость меняет колонка, не Кеша
        hit = quick_control(text)
        if hit and is_error_reply(hit[1]):
            sfx.play("error")
        return hit

    def _on_wake(self):
        duck.duck()
        set_state(State.WAKE)
        sfx.play("wake")
        sfx.wait_quiet(0.15)     # «бульк» короткий — не ждём лишнего

    def step(self):
        """Одна итерация цикла (вынесено для тестов). Звук, приглушённый на «Кеша», возвращаем
        в конце — когда окно команд закрылось."""
        try:
            self._step()
        finally:
            duck.restore()

    def _step(self):
        set_state(State.IDLE)
        if self.ww is not None:
            # клавишу могли нажать, пока Кеша говорила — тогда сразу слушаем
            # приглушение и «бульк» детектор делает сам, не закрывая микрофон: иначе
            # «Кеша, открой браузер» одним духом теряло начало команды
            woke = []
            on_wake = lambda: (woke.append(1), self._on_wake())
            if self._armed_at is not None:
                heard = False
            elif getattr(self.ww, "supports_on_wake", False):
                heard = self.ww.wait_for_wake(should_pause=is_mic_blocked, on_wake=on_wake)
            else:
                heard = self.ww.wait_for_wake(should_pause=is_mic_blocked)
            if self._take_arm():
                self._active_window(ARM_TIMEOUT)
                return
            if not heard:
                return
            if not woke:
                self._on_wake()
            pre = getattr(self.ww, "wake_audio", None)
            start = pre.tobytes() if pre is not None and len(pre) else None
            self._active_window(WAKE_LISTEN_TIMEOUT, start_audio=start)
            return

        text = self._listen(None, passive=True)
        info = getattr(self.vad, "last_info", {}) or {}
        started = time.time() - info.get("duration_sec", 0) - 0.8
        if text and self._take_arm(started):
            cmd = _clean(text)
            if cmd:
                self._process(cmd)
            self._active_window(MIC_ACTIVE_WINDOW, first_ai=False)
            return
        if text and not _has_wake(text):
            self._quick(text)
            return
        if not text:
            return
        self._on_wake()
        cmd = _clean(text)
        if cmd:
            self._process(cmd)
            self._active_window(MIC_ACTIVE_WINDOW, first_ai=False)
        else:
            self._active_window(WAKE_LISTEN_TIMEOUT)

    def run(self):
        global _current
        _current = self
        self._speak(persona.startup_phrase())
        while True:
            try:
                self.step()
            except Exception as e:
                print("[voice]", e)
                set_state(State.ERROR, error=str(e))
                sfx.play("error")
                time.sleep(1)


def arm():
    """Активировать микрофон без слова (горячая клавиша, кнопка, значок)."""
    if _current is not None:
        _current.arm()
    elif not sfx.alarm_stop():
        print("[voice] голосовой цикл не запущен")


def _register_hotkey():
    if not HOTKEY:
        return
    try:
        import keyboard
        keyboard.add_hotkey(HOTKEY, arm)
        print(f"[voice] горячая клавиша {HOTKEY}: слушать без слова «Кеша»")
    except Exception as e:
        print(f"[voice] горячая клавиша недоступна: {e}")


def _legacy_loop():
    """Старый цикл на Google-распознавателе — страховка, если новый стек не поднялся."""
    from .recognizer import Recognizer
    rec = Recognizer()
    say(persona.startup_phrase())
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


def _gigaam_verify(rec):
    """Вторая ступень openWakeWord: GigaAM распознаёт последние 1.8 с — есть ли там «Кеша»."""
    local = getattr(rec, "local", rec)

    def verify(pcm, peak=0.0):
        with _stt_lock:
            text = local.recognize(pcm.tobytes())
        ok = _has_wake(text) or (peak >= 0.9 and near_kesha(text))
        if ok:   # «нет» не печатаем: на любой речи рядом их десятки
            print(f"[voice] wake word подтверждён: {text!r} (пик {peak:.2f})")
        return ok
    return verify


def _quick_phrases(rec, loop_ref):
    """Короткие фразы из потока openWakeWord -> GigaAM -> команды управления. Своим потоком:
    распознавание не должно тормозить чтение микрофона."""
    local = getattr(rec, "local", rec)
    q = queue.Queue(maxsize=2)

    def worker():
        while True:
            pcm = q.get()
            try:
                with _stt_lock:
                    text = local.recognize(pcm.tobytes())
                if text and not _has_wake(text) and loop_ref():
                    loop_ref()._quick(text)
            except Exception as e:
                print("[voice] быстрая команда:", e)

    threading.Thread(target=worker, daemon=True, name="quick-control").start()

    def on_phrase(pcm):
        try:
            q.put_nowait(pcm)
        except queue.Full:
            pass
    return on_phrase


def _pick_wake_detector(rec=None):
    """Порядок: Porcupine со своим .ppn «Кеша» -> openWakeWord -> свой CNN -> GigaAM по тексту.
    Porcupine без .ppn не берём: он слушал бы английское «computer», а не «Кеша»."""
    from .wake_word import find_custom_files
    from .oww_wake import OwwWakeDetector
    from .local_wake import LocalWakeDetector
    tried = []
    if find_custom_files()[0]:
        from .wake_word import WakeWordDetector
        tried.append(("Porcupine", WakeWordDetector))
    verify = _gigaam_verify(rec) if rec is not None else None
    on_phrase = _quick_phrases(rec, lambda: _current) if rec is not None else None
    tried += [("openWakeWord", lambda: OwwWakeDetector(verify=verify, on_phrase=on_phrase)),
              ("свой детектор", LocalWakeDetector)]
    for name, cls in tried:
        try:
            ww = cls()
            thr = getattr(ww, "threshold", None)
            print(f"[voice] wake word: {ww.label}" + (f" (порог {thr:.2f})" if thr is not None else ""))
            return ww
        except Exception as e:
            print(f"[voice] {name} недоступен ({e})")
    print(f"[voice] слово-активатор ({', '.join(WAKE_WORDS)}) ищу через GigaAM. "
          f"Обучить детектор: python tools/train_oww.py all")
    return None


def start_voice_loop():
    try:
        from .gigaam_recognizer import GigaAMRecognizer
        from .vad_recorder import VADRecorder
        rec = GigaAMRecognizer()
        if STT_ENGINE == "aqua":
            import aqua_stt
            if aqua_stt.available():
                rec = aqua_stt.AquaRecognizer(rec)
                print("[voice] STT: Aqua Avalon (запасной — GigaAM)")
            else:
                print("[voice] STT: AQUA_API_KEY не задан, работаю на GigaAM")
        vad = VADRecorder()
    except Exception as e:
        print(f"[voice] новый стек недоступен ({e}), запускаю старый Google-распознаватель")
        set_state(State.ERROR, error=str(e))
        _legacy_loop()
        return

    ww = _pick_wake_detector(rec)
    _register_hotkey()
    VoiceLoop(rec, vad, ww).run()
