"""Запись с микрофона до тишины. Речь определяет Silero VAD (нейросеть); нет его — webrtcvad;
нет и его — запасной VAD по энергии. Движок: config.VAD_ENGINE."""
import collections
import time

import numpy as np
import sounddevice as sd

import config
from config import MIN_SPEECH_DB, WAKE_SILENCE_SEC, VOICE_MARGIN_DB, VOICE_KEEP_SEC
from .loudness import speech_db
from .mic import open_stream

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
        self.silero = None           # нейросетевой VAD; None — работаем на webrtcvad
        if getattr(config, "VAD_ENGINE", "silero") == "silero":
            from . import silero_gate
            self.silero = silero_gate.load(getattr(config, "SILERO_VAD_THRESHOLD", 0.5))
        self.noise_db = None         # уровень фона (dBFS), замеряется по кадрам без речи
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
        self._voice_db = None        # громкость голоса из последнего «Кеша»
        self._voice_at = 0.0

    def _voice_floor(self, start_audio):
        """Порог речи по голосу пользователя (dBFS) или None, если «Кеша» давно не звали."""
        now = time.time()
        if start_audio:
            # 95-й перцентиль: в начале записи и фон до «Кеша», громкий кусок — это голос
            self._voice_db, self._voice_at = speech_db(start_audio, pct=95), now
        if self._voice_db is None or now - self._voice_at > VOICE_KEEP_SEC:
            return None
        return self._voice_db - VOICE_MARGIN_DB

    def _is_speech(self, frame):
        pcm = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
        rms = float(np.sqrt(np.mean(pcm * pcm)))
        if self.silero is not None:
            # кадр скармливаем всегда: сети нужен непрерывный звук, а не только громкие куски
            return self.silero.is_speech(frame) and rms >= self.min_rms
        if self.vad is not None:
            # webrtcvad «слышит речь» и в тишине −70 dB — отсекаем по громкости
            return rms >= self.min_rms and self.vad.is_speech(frame, SAMPLE_RATE)
        return rms > max(self.energy_threshold, self.min_rms)

    def _track_noise(self, frame):
        """Скользящий уровень фона по кадрам без речи — виден в журнале рядом с громкостью фразы."""
        pcm = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
        db = 20 * float(np.log10((float(np.sqrt(np.mean(pcm * pcm))) + 1e-9) / 32768))
        self.noise_db = db if self.noise_db is None else 0.97 * self.noise_db + 0.03 * db

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
        floor_db = self._voice_floor(start_audio)
        base_rms = self.min_rms
        if floor_db is not None:
            self.min_rms = max(base_rms, 32768.0 * 10 ** (floor_db / 20))
        try:
            audio = self._record_frames(max_wait, max_seconds, should_pause, start_audio)
        finally:
            self.min_rms = base_rms
        if audio and floor_db is not None:
            self._voice_at = time.time()      # пользователь ещё говорит с Кешей — порог держим
        self.last_info["voice_floor_db"] = floor_db
        return audio

    def _record_frames(self, max_wait, max_seconds, should_pause, start_audio=None):
        max_seconds = max_seconds or self.max_seconds
        t_begin = time.time()
        preroll = collections.deque(maxlen=self.preroll_frames)
        frames = []
        speech_run = 0
        silence_run = 0
        triggered = False
        stopped_by = "no_speech"
        silence_frames = self.silence_frames
        if self.silero is not None:
            self.silero.reset()
        if start_audio:
            # сразу после «Кеша» люди медлят перед командой — пауза длиннее, фразу не режем
            silence_frames = max(silence_frames, int(round(WAKE_SILENCE_SEC * 1000 / FRAME_MS)))
            n = len(start_audio) // (2 * FRAME_SAMPLES) * 2 * FRAME_SAMPLES
            frames = [start_audio[i:i + 2 * FRAME_SAMPLES] for i in range(0, n, 2 * FRAME_SAMPLES)]
            triggered = bool(frames)
            flags = [self._is_speech(f) for f in frames]    # по порядку: нейросети нужен ход времени
            for said in reversed(flags):        # тишина в конце начала уже считается паузой
                if said:
                    break
                silence_run += 1
            silence_run = min(silence_run, silence_frames - 1)

        # start_audio пришёл из детектора — читаем ровно с места, где он остановился
        with open_stream(SAMPLE_RATE, FRAME_SAMPLES, self.device, resume=bool(start_audio)) as stream:
            while True:
                data, _overflow = stream.read(FRAME_SAMPLES)
                frame = bytes(data)

                # после «Кеша» микрофон блокирует только наш «бульк»: его не слушаем, но и
                # уже записанное «Кеша, громче» не выбрасываем — раньше команда тут и пропадала
                if should_pause is not None and should_pause():
                    if start_audio:
                        continue
                    preroll.clear()
                    frames = []
                    triggered = False
                    speech_run = silence_run = 0
                    t_begin = time.time()
                    continue

                speech = self._is_speech(frame)

                if not triggered:
                    if not speech:
                        self._track_noise(frame)
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
                    if silence_run >= silence_frames:
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
            "vad": "silero" if self.silero is not None else "webrtcvad" if self.vad is not None else "energy",
            "noise_db": None if self.noise_db is None else round(self.noise_db, 1),
            "stopped_by": stopped_by,
            "duration_sec": len(audio) / 2 / SAMPLE_RATE,
            "elapsed_sec": time.time() - t_begin,
        }
        return audio
