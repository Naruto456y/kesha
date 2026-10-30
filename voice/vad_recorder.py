"""Запись с микрофона до тишины. webrtcvad; если не установлен — запасной VAD по энергии."""
import collections
import time

import numpy as np
import sounddevice as sd

from config import MIN_SPEECH_DB
from .loudness import speech_db

try:
    import webrtcvad
except Exception:
    webrtcvad = None

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000   # 480 сэмплов = 960 байт


class VADRecorder:
    def __init__(self, aggressiveness=2, silence_sec=0.65, max_seconds=15.0,
                 preroll_ms=300, start_frames=3, keep_tail_ms=200,
                 device=None, energy_threshold=500, min_db=None):
        self.vad = webrtcvad.Vad(aggressiveness) if webrtcvad is not None else None
        self.silence_frames = int(round(silence_sec * 1000 / FRAME_MS))   # 0.8 с -> 27 кадров
        self.max_seconds = max_seconds
        self.preroll_frames = max(1, preroll_ms // FRAME_MS)
        self.start_frames = start_frames
        self.keep_tail = keep_tail_ms // FRAME_MS
        self.device = device
        self.energy_threshold = energy_threshold
        self.min_db = MIN_SPEECH_DB if min_db is None else min_db
        self.min_rms = 32768.0 * 10 ** ((self.min_db - 2) / 20)   # кадр чуть тише порога ещё речь
        self.last_info = {}
        self.speech_active = False   # идёт запись фразы (речь началась, тишины ещё нет)

    def _is_speech(self, frame):
        pcm = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
        rms = float(np.sqrt(np.mean(pcm * pcm)))
        if self.vad is not None:
            # webrtcvad «слышит речь» и в тишине −70 dB — отсекаем по громкости
            return rms >= self.min_rms and self.vad.is_speech(frame, SAMPLE_RATE)
        return rms > self.energy_threshold

    def record(self, max_wait=None, max_seconds=None, should_pause=None, start_audio=None):
        """Ждёт начала речи (до max_wait сек, None = бесконечно), пишет до 0.8 с тишины.
        Возвращает PCM int16 16 kHz mono; b"" если речи не было.
        Причина остановки — в self.last_info['stopped_by']: silence | max | no_speech | quiet.
        Слишком тихую запись (шорох) выбрасываем и ждём дальше, пока не выйдет max_wait.
        start_audio — уже записанное начало фразы («Кеша…» из детектора): пишем дальше без паузы."""
        deadline = None if max_wait is None else time.time() + max_wait
        while True:
            left = None if deadline is None else deadline - time.time()
            audio = self._record_once(left, max_seconds, should_pause, start_audio)
            start_audio = None
            if audio or self.last_info.get("stopped_by") != "quiet" or (left is not None and deadline - time.time() < 0.3):
                return audio

    def _record_once(self, max_wait, max_seconds, should_pause, start_audio=None):
        max_seconds = max_seconds or self.max_seconds
        t_begin = time.time()
        preroll = collections.deque(maxlen=self.preroll_frames)
        frames = []
        speech_run = 0
        silence_run = 0
        triggered = False
        stopped_by = "no_speech"
        if start_audio:
            n = len(start_audio) // (2 * FRAME_SAMPLES) * 2 * FRAME_SAMPLES
            frames = [start_audio[i:i + 2 * FRAME_SAMPLES] for i in range(0, n, 2 * FRAME_SAMPLES)]
            triggered = bool(frames)
            for f in reversed(frames):          # тишина в конце начала уже считается паузой
                if self._is_speech(f):
                    break
                silence_run += 1
            silence_run = min(silence_run, self.silence_frames - 1)

        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=FRAME_SAMPLES,
                               channels=1, dtype="int16", device=self.device) as stream:
            while True:
                data, _overflow = stream.read(FRAME_SAMPLES)
                frame = bytes(data)

                if should_pause is not None and should_pause():
                    preroll.clear()
                    frames = []
                    triggered = False
                    speech_run = silence_run = 0
                    t_begin = time.time()
                    continue

                speech = self._is_speech(frame)

                if not triggered:
                    preroll.append(frame)
                    speech_run = speech_run + 1 if speech else 0
                    if speech_run >= self.start_frames:
                        triggered = True
                        self.speech_active = True
                        frames = list(preroll)
                        silence_run = 0
                    elif max_wait is not None and time.time() - t_begin > max_wait:
                        break
                else:
                    frames.append(frame)
                    silence_run = 0 if speech else silence_run + 1
                    if silence_run >= self.silence_frames:
                        stopped_by = "silence"
                        cut = max(0, silence_run - self.keep_tail)
                        if cut:
                            del frames[-cut:]
                        break
                    if len(frames) * FRAME_MS / 1000.0 >= max_seconds:
                        stopped_by = "max"
                        break

        self.speech_active = False
        audio = b"".join(frames) if triggered else b""
        if audio and speech_db(audio) < self.min_db:
            stopped_by, audio = "quiet", b""      # шорох/тишина — в GigaAM не отдаём
        self.last_info = {
            "vad": "webrtcvad" if self.vad is not None else "energy",
            "stopped_by": stopped_by,
            "duration_sec": len(audio) / 2 / SAMPLE_RATE,
            "elapsed_sec": time.time() - t_begin,
        }
        return audio
