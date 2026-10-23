"""Запись с микрофона до тишины. webrtcvad; если не установлен — запасной VAD по энергии."""
import collections
import time

import numpy as np
import sounddevice as sd

try:
    import webrtcvad
except Exception:
    webrtcvad = None

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000   # 480 сэмплов = 960 байт


class VADRecorder:
    def __init__(self, aggressiveness=2, silence_sec=0.8, max_seconds=15.0,
                 preroll_ms=300, start_frames=3, keep_tail_ms=200,
                 device=None, energy_threshold=500):
        self.vad = webrtcvad.Vad(aggressiveness) if webrtcvad is not None else None
        self.silence_frames = int(round(silence_sec * 1000 / FRAME_MS))   # 0.8 с -> 27 кадров
        self.max_seconds = max_seconds
        self.preroll_frames = max(1, preroll_ms // FRAME_MS)
        self.start_frames = start_frames
        self.keep_tail = keep_tail_ms // FRAME_MS
        self.device = device
        self.energy_threshold = energy_threshold
        self.last_info = {}

    def _is_speech(self, frame):
        if self.vad is not None:
            return self.vad.is_speech(frame, SAMPLE_RATE)
        pcm = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
        return float(np.sqrt(np.mean(pcm * pcm))) > self.energy_threshold

    def record(self, max_wait=None, max_seconds=None, should_pause=None):
        """Ждёт начала речи (до max_wait сек, None = бесконечно), пишет до 0.8 с тишины.
        Возвращает PCM int16 16 kHz mono; b"" если речи не было.
        Причина остановки — в self.last_info['stopped_by']: silence | max | no_speech."""
        max_seconds = max_seconds or self.max_seconds
        t_begin = time.time()
        preroll = collections.deque(maxlen=self.preroll_frames)
        frames = []
        speech_run = 0
        silence_run = 0
        triggered = False
        stopped_by = "no_speech"

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

        audio = b"".join(frames) if triggered else b""
        self.last_info = {
            "vad": "webrtcvad" if self.vad is not None else "energy",
            "stopped_by": stopped_by,
            "duration_sec": len(audio) / 2 / SAMPLE_RATE,
            "elapsed_sec": time.time() - t_begin,
        }
        return audio
