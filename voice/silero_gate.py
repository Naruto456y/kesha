"""
Нейросетевой детектор речи Silero VAD (ONNX, ~2 МБ, <1 мс на кадр).
webrtcvad считает речью музыку, стук клавиш и шум вентилятора; Silero обучен отличать
именно человеческий голос, поэтому фраза не обрывается и не тянется из-за фона.

Модели нужны куски ровно по 512 сэмплов (32 мс), а запись идёт кадрами по 30 мс —
поэтому копим звук и отдаём вероятность по последнему полному куску.
"""
import numpy as np

RATE = 16000
WINDOW = 512


class SileroGate:
    def __init__(self, threshold=0.5):
        import torch
        from silero_vad import load_silero_vad
        self._torch = torch
        self._model = load_silero_vad(onnx=True)
        self.threshold = threshold
        self.reset()

    def reset(self):
        self._model.reset_states()
        self._buf = np.zeros(0, dtype=np.float32)
        self.prob = 0.0

    def feed(self, frame: bytes) -> float:
        """Кадр PCM int16 любой длины -> вероятность речи (0..1) на этот момент."""
        x = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
        self._buf = np.concatenate([self._buf, x])
        while len(self._buf) >= WINDOW:
            chunk, self._buf = self._buf[:WINDOW], self._buf[WINDOW:]
            self.prob = float(self._model(self._torch.from_numpy(chunk), RATE))
        return self.prob

    def is_speech(self, frame: bytes) -> bool:
        return self.feed(frame) >= self.threshold


def load(threshold=0.5):
    """SileroGate или None, если пакет silero-vad не установлен."""
    try:
        return SileroGate(threshold)
    except Exception as e:
        print(f"[vad] Silero VAD недоступен ({e}), работаю на webrtcvad")
        return None
