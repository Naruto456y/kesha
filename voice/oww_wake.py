"""
Слово «Кеша» на openWakeWord (бесплатно, офлайн, Apache-2.0).

Готовая сеть openWakeWord (melspectrogram + embedding, 2.4 МБ ONNX, обучена Google на
тысячах часов речи) превращает звук в «смысловые» признаки, а поверх неё учится
крошечная голова (≈200 тыс. параметров) на твоих записях «Кеша». Поэтому хватает
40 записей, а работа в фоне стоит ~2 мс CPU на каждые 80 мс звука.

Обучение: python tools/train_oww.py all. Голова: data/wake/oww_head.pt.
OwwWakeDetector — тот же интерфейс, что у Porcupine (wait_for_wake / stop / label).
"""
import threading
import time
from pathlib import Path

import numpy as np

from config import DATA_DIR

WAKE_DIR = DATA_DIR / "wake"
OWW_DIR = WAKE_DIR / "oww"
HEAD_PATH = WAKE_DIR / "oww_head.pt"
RATE = 16000
CHUNK = 1280            # 80 мс — шаг openWakeWord
WAKE_KEEP = int(1.8 * RATE)   # столько звука до срабатывания отдаём в запись команды (там и «Кеша»)
FRAMES = 16             # окно головы: 16 эмбеддингов ≈ 1.3 с
CLIP = 32000            # 2 с звука дают ровно 16 эмбеддингов
EMB = 96
# после reset() буфер признаков забит нулями: первые ~1 с «тишина -> звук» похожа на начало слова
WARMUP = 12
_URL = "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/{}.onnx"
FEATURE_MODELS = ("melspectrogram", "embedding_model")
# короткая фраза в потоке (для команд без «Кеша»: «громче», «пауза»): громче фона на 12 дБ,
# 0.3–2.5 с, конец — 0.4 с тишины
PHRASE_DB, PHRASE_MIN, PHRASE_MAX, PHRASE_GAP = 12.0, 4, 31, 5


def ensure_feature_models():
    """Скачать две ONNX-модели признаков (один раз, 2.4 МБ)."""
    import requests
    OWW_DIR.mkdir(parents=True, exist_ok=True)
    for name in FEATURE_MODELS:
        path = OWW_DIR / f"{name}.onnx"
        if not path.exists():
            r = requests.get(_URL.format(name), timeout=60)
            r.raise_for_status()
            path.write_bytes(r.content)
    return [OWW_DIR / f"{n}.onnx" for n in FEATURE_MODELS]


def feature_extractor():
    from openwakeword.utils import AudioFeatures
    mel, emb = ensure_feature_models()
    return AudioFeatures(str(mel), str(emb), sr=RATE, inference_framework="onnx")


def build_head():
    import torch.nn as nn
    return nn.Sequential(nn.Flatten(), nn.Linear(FRAMES * EMB, 128), nn.LayerNorm(128), nn.ReLU(),
                         nn.Dropout(0.3), nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1))


def load_head(path=HEAD_PATH):
    import torch
    data = torch.load(path, map_location="cpu", weights_only=True)
    net = build_head()
    net.load_state_dict(data["state"])
    net.eval()
    return net, float(data["threshold"])


def to_int16(wav):
    return (np.clip(np.asarray(wav, dtype=np.float32), -1, 1) * 32767).astype(np.int16)


def embed_clips(fe, clips, batch=64):
    """Клипы float32 по CLIP сэмплов -> (N, FRAMES, EMB)."""
    return fe.embed_clips(np.stack([to_int16(c) for c in clips]), batch_size=batch)


def stream_scores(net, fe, wav):
    """Оценки длинной записи с шагом 80 мс — как в живом потоке."""
    import torch
    wav = np.concatenate([np.zeros(CLIP - CHUNK, dtype=np.float32), np.asarray(wav, dtype=np.float32)])
    emb = fe.embed_clips(to_int16(wav)[None], batch_size=1)[0]
    if len(emb) < FRAMES:
        return np.zeros(0)
    x = np.stack([emb[i:i + FRAMES] for i in range(len(emb) - FRAMES + 1)])
    with torch.no_grad():
        return torch.sigmoid(net(torch.from_numpy(x).float()).squeeze(1)).numpy()[WARMUP:]


class OwwWakeDetector:
    """Две ступени: оценка >= threshold — сразу «Кеша»; оценка >= soft_threshold
    (далеко, нечётко, но и «Наташа» тоже) — когда звук закончился, последние 1.8 с
    проверяет verify(int16, пик) (GigaAM: распознал ли «Кеша»)."""
    label = "openWakeWord «Кеша»"
    supports_on_wake = True     # wait_for_wake(on_wake=...) и запись с самого «Кеша» (wake_audio)

    def __init__(self, head_path=HEAD_PATH, device=None, hits_needed=2, verify=None, soft_threshold=0.5,
                 on_phrase=None):
        if not Path(head_path).exists():
            raise RuntimeError(f"нет {head_path} — запусти python tools/train_oww.py all")
        self.net, self.threshold = load_head(head_path)
        self.fe = feature_extractor()
        self.device, self.hits_needed = device, hits_needed
        self.verify, self.soft_threshold = verify, soft_threshold
        self.on_phrase = on_phrase      # on_phrase(int16) — короткая фраза без «Кеша»
        self._floor = -60.0
        self.last_score, self.last_event = 0.0, None
        self._stop = False
        self.reset()

    def stop(self):
        self._stop = True

    def reset(self):
        self.fe.reset()
        self._audio = np.zeros(40 * CHUNK, dtype=np.int16)      # 3.2 с: хватит на фразу до PHRASE_MAX
        self._hits = self._soft = 0
        self._peak = 0.0
        self._warm = WARMUP
        self._voiced = self._quiet = 0
        self._woke = False
        self.wake_audio = None      # звук с «Кеша» до сих пор — начало записи команды

    def feed(self, chunk_int16, hits):
        """Один шаг 80 мс -> (подряд идущих попаданий, сработало ли)."""
        import torch
        self.fe._streaming_features(chunk_int16)
        x = torch.from_numpy(self.fe.get_features(FRAMES)).float()
        with torch.no_grad():
            p = float(torch.sigmoid(self.net(x)))
        self.last_score = p
        hits = hits + 1 if p >= self.threshold else 0
        return hits, hits >= self.hits_needed

    def _phrase(self, chunk):
        """Простой VAD по громкости: закончилась короткая фраза — отдать её on_phrase."""
        if self.on_phrase is None:
            return
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2))) + 1e-9
        db = 20 * np.log10(rms / 32768)
        if db > self._floor + PHRASE_DB:
            self._voiced += 1
            self._quiet = 0
            return
        if db < self._floor + 6:
            self._floor = 0.95 * self._floor + 0.05 * db
        if not self._voiced:
            return
        self._quiet += 1
        if self._quiet < PHRASE_GAP:
            return
        n, self._voiced, self._quiet = self._voiced, 0, 0
        if PHRASE_MIN <= n <= PHRASE_MAX and not self._woke:
            self.on_phrase(self._audio[-(n + PHRASE_GAP + 2) * CHUNK:].copy())
        self._woke = False

    def step(self, chunk_int16) -> bool:
        """Один шаг 80 мс с двумя ступенями. last_event — (пик, как решили) после каждого звука."""
        self.last_event = None
        self._audio = np.concatenate([self._audio[len(chunk_int16):], chunk_int16])
        self._phrase(chunk_int16)
        self._hits, fired = self.feed(chunk_int16, self._hits)
        p = self.last_score
        if self._warm:
            self._warm -= 1
            self._hits = self._soft = 0
            return False
        # с проверкой GigaAM проверяем всё: на живой речи (видео) акустика тоже даёт 0.99+
        if fired and self.verify is None:
            self.last_event = (p, "уверенно")
            tail = self._audio[-WAKE_KEEP:].copy()
            self.reset()
            self.wake_audio = tail
            return True
        if p >= self.soft_threshold:
            self._soft += 1
            self._peak = max(self._peak, p)
            return False
        soft, peak, self._soft, self._peak = self._soft, self._peak, 0, 0.0
        self._woke = self._woke or soft >= self.hits_needed
        if soft < self.hits_needed:
            return False
        if self.verify is None:
            self.last_event = (peak, "мимо")
            return False
        ok = bool(self.verify(self._audio[-int(1.8 * RATE):], peak))
        self.last_event = (peak, "GigaAM: да" if ok else "GigaAM: нет")
        if ok:
            tail = self._audio[-WAKE_KEEP:].copy()
            self.reset()
            self.wake_audio = tail
        return ok

    def wait_for_wake(self, timeout=None, should_pause=None, on_wake=None):
        """on_wake() — приглушить звук и «бульк»: делаем это в потоке, а микрофон дальше пишем
        в wake_audio. Иначе «Кеша, открой браузер» одним духом теряло начало команды."""
        import sounddevice as sd
        self._stop = False
        deadline = None if timeout is None else time.time() + timeout
        self.reset()
        with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, channels=1,
                               dtype="int16", device=self.device) as stream:
            while not self._stop:
                if deadline is not None and time.time() > deadline:
                    return False
                data, _ = stream.read(CHUNK)
                if should_pause is not None and should_pause():
                    self._hits = self._soft = self._voiced = self._quiet = 0   # Кеша говорит сама
                    continue
                if self.step(np.frombuffer(bytes(data), dtype=np.int16)):
                    if on_wake is not None:
                        self._record_during(stream, on_wake)
                    return True
        return False

    def _record_during(self, stream, fn):
        t = threading.Thread(target=fn, daemon=True, name="on-wake")
        t.start()
        parts = [self.wake_audio]
        while t.is_alive():
            data, _ = stream.read(CHUNK)
            parts.append(np.frombuffer(bytes(data), dtype=np.int16))
        self.wake_audio = np.concatenate(parts)

    def close(self):
        pass
