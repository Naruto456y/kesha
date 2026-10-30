"""
Свой детектор слова «Кеша», обученный на твоих записях (бесплатно, офлайн, без ключей).
Обучение: python tools/train_wake.py. Модель: data/wake/model.pt.

LocalWakeDetector — тот же интерфейс, что у Porcupine (wait_for_wake / stop / label),
поэтому голосовой цикл работает с ним без изменений.
"""
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

from config import DATA_DIR

WAKE_DIR = DATA_DIR / "wake"
MODEL_PATH = WAKE_DIR / "model.pt"
RATE = 16000
WINDOW = RATE           # окно 1 с
HOP = RATE // 10        # шаг 0.1 с
N_MELS = 40


def _mel():
    import torchaudio
    return torchaudio.transforms.MelSpectrogram(
        sample_rate=RATE, n_fft=400, hop_length=160, n_mels=N_MELS)


_mel_tf = None


def features(wav):
    """float32 [-1, 1], ровно WINDOW сэмплов -> тензор (1, N_MELS, 101)."""
    import torch
    global _mel_tf
    if _mel_tf is None:
        _mel_tf = _mel()
    x = torch.from_numpy(np.asarray(wav, dtype=np.float32))
    m = torch.log(_mel_tf(x) + 1e-6)
    return (m - m.mean()).unsqueeze(0)


ARCH = 2   # 2: GroupNorm вместо BatchNorm — одинаково ведёт себя при обучении и в работе


def build_net():
    import torch.nn as nn
    def block(i, o):
        return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.GroupNorm(4, o), nn.ReLU(), nn.MaxPool2d(2))
    return nn.Sequential(block(1, 16), block(16, 32), block(32, 64),
                         nn.AdaptiveMaxPool2d(1), nn.Flatten(), nn.Dropout(0.2), nn.Linear(64, 1))


def load_model(path=MODEL_PATH):
    import torch
    data = torch.load(path, map_location="cpu", weights_only=True)
    if data.get("arch", 1) != ARCH:
        raise RuntimeError("модель старого формата — переобучи: python tools/train_wake.py train")
    net = build_net()
    net.load_state_dict(data["state"])
    net.eval()
    return net, float(data["threshold"])


def score(net, wav) -> float:
    import torch
    with torch.no_grad():
        return float(torch.sigmoid(net(features(wav).unsqueeze(0))))


def stream_scores(net, wav, batch=256):
    """Оценки всех окон длинной записи с шагом HOP — как в живом потоке, но пачками."""
    import torch
    wav = np.concatenate([np.zeros(WINDOW - HOP, dtype=np.float32), np.asarray(wav, dtype=np.float32)])
    starts = range(0, len(wav) - WINDOW + 1, HOP)
    out = []
    with torch.no_grad():
        idx = list(starts)
        for i in range(0, len(idx), batch):
            x = torch.stack([features(wav[s:s + WINDOW]) for s in idx[i:i + batch]])
            out.append(torch.sigmoid(net(x).squeeze(1)))
    return torch.cat(out).numpy() if out else np.zeros(0)


def fires(scores, threshold, hits_needed=2):
    """Сработал бы детектор: hits_needed окон подряд выше порога."""
    run = 0
    for p in scores:
        run = run + 1 if p >= threshold else 0
        if run >= hits_needed:
            return True
    return False


class LocalWakeDetector:
    label = "своё слово «Кеша»"

    def __init__(self, model_path=MODEL_PATH, device=None, hits_needed=2, cooldown=1.5):
        if not Path(model_path).exists():
            raise RuntimeError(f"нет модели {model_path} — запусти python tools/train_wake.py")
        self.net, self.threshold = load_model(model_path)
        self.device, self.hits_needed, self.cooldown = device, hits_needed, cooldown
        self._stop = False

    def stop(self):
        self._stop = True

    def feed(self, buf, hits):
        """Один шаг: буфер float32 -> (новое число подряд идущих попаданий, сработало ли)."""
        p = score(self.net, buf[-WINDOW:])
        hits = hits + 1 if p >= self.threshold else 0
        return hits, hits >= self.hits_needed

    def wait_for_wake(self, timeout=None, should_pause=None):
        self._stop = False
        deadline = None if timeout is None else time.time() + timeout
        buf = np.zeros(WINDOW, dtype=np.float32)
        hits = 0
        with sd.RawInputStream(samplerate=RATE, blocksize=HOP, channels=1,
                               dtype="int16", device=self.device) as stream:
            while not self._stop:
                if deadline is not None and time.time() > deadline:
                    return False
                data, _ = stream.read(HOP)
                if should_pause is not None and should_pause():
                    buf[:] = 0
                    hits = 0
                    continue
                chunk = np.frombuffer(bytes(data), dtype=np.int16).astype(np.float32) / 32768.0
                buf = np.concatenate([buf[HOP:], chunk])
                hits, fired = self.feed(buf, hits)
                if fired:
                    return True
        return False

    def close(self):
        pass
