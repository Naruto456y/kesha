"""
Распознавание интонации (волна 5): если на Кешу кричат — она обижается.
Громкость речи меряем в dBFS по кадрам 30 мс; «крик» — когда речь громче
порога SHOUT_DB И заметно громче обычной речи этого пользователя.
"""

from collections import deque

import numpy as np

from config import SHOUT_DB, SHOUT_MARGIN_DB

FRAME = 480   # 30 мс при 16 кГц


def speech_db(pcm_bytes: bytes) -> float:
    """Уровень речи: 80-й перцентиль громкости кадров (паузы не тянут вниз)."""
    pcm = np.frombuffer(pcm_bytes[: len(pcm_bytes) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768.0
    if len(pcm) < FRAME:
        return -120.0
    frames = pcm[: len(pcm) // FRAME * FRAME].reshape(-1, FRAME)
    rms = np.sqrt(np.mean(frames * frames, axis=1)) + 1e-9
    return float(np.percentile(20 * np.log10(rms), 80))


class ShoutDetector:
    def __init__(self, threshold_db=SHOUT_DB, margin_db=SHOUT_MARGIN_DB, history=15):
        self.threshold = threshold_db
        self.margin = margin_db
        self.levels = deque(maxlen=history)   # обычная речь пользователя

    def baseline(self):
        return float(np.median(self.levels)) if self.levels else None

    def check(self, pcm_bytes: bytes) -> bool:
        level = speech_db(pcm_bytes)
        base = self.baseline()
        if base is None:
            shouting = level > self.threshold + 4
        else:
            shouting = level > self.threshold and level - base >= self.margin
        if not shouting:
            self.levels.append(level)
        return shouting
