"""
Обучение «Кеша» на openWakeWord (рекомендуется вместо train_wake.py — точнее при тех же записях).

    python tools/train_oww.py record    # ~5 минут: слово ×40 + похожие слова + речь + фон
    python tools/train_oww.py train     # 1–3 минуты -> data/wake/oww_head.pt
    python tools/train_oww.py test      # вживую: говори, увидишь «СЛЫШУ»
    python tools/train_oww.py all       # record + train
    python tools/train_oww.py threshold 0.9   # поменять порог вручную
    python tools/train_oww.py far      # дописать «Кеша» издалека и нечётко
    python tools/train_oww.py speech 120  # дописать N секунд обычной речи (меньше ложных срабатываний)

Записи общие с train_wake.py (data/wake/pos, data/wake/neg): если уже записывал — сразу train.
"""
import random
import sys
import time

import numpy as np

from train_wake import (POS_DIR, NEG_DIR, RATE, load_wavs, trim_word, tts_samples, stretch,
                        cmd_record, streak, HARD_WORDS, NEG_WORDS, record_seconds, save_wav)
from voice.oww_wake import (HEAD_PATH, CLIP, WAKE_DIR, feature_extractor, embed_clips,
                            build_head, stream_scores)


def bg(noise, rng, n=CLIP):
    """Фон: кусок твоих записей или тихий шум микрофона разной громкости."""
    if len(noise) > n and rng.random() < 0.7:
        s = rng.integers(0, len(noise) - n)
        return noise[s:s + n] * rng.uniform(0.3, 2.0)
    return rng.normal(0, 10 ** rng.uniform(-3.7, -1.7), n).astype(np.float32)


def far(word, rng):
    """«Издалека»: эхо комнаты (синтетический отклик), завал верхов, тише."""
    from scipy.signal import fftconvolve, lfilter
    n = int(rng.uniform(0.15, 0.5) * RATE)
    ir = rng.normal(0, 1, n).astype(np.float32) * np.exp(-np.arange(n) / (n / rng.uniform(4, 8)))
    ir[0] = rng.uniform(1.5, 4)                          # прямой звук
    y = fftconvolve(word, ir)[: len(word) + n // 2]
    a = rng.uniform(0.3, 0.7)
    y = lfilter([1 - a], [1, -a], y)                     # простой фильтр нижних частот
    return (y / (np.abs(y).max() + 1e-6) * np.abs(word).max() * rng.uniform(0.2, 0.6)).astype(np.float32)


def aug(word, rng):
    w = stretch(word, rng)
    return far(w, rng) if rng.random() < 0.35 else w


def place(word, noise, rng):
    """Слово заканчивается в последних 0.1–0.6 с окна — так его видит поток в момент срабатывания."""
    word = word[: int(CLIP * 0.6)]
    win = bg(noise, rng).copy()
    end = CLIP - int(rng.uniform(0.1, 0.6) * RATE)
    start = max(0, end - len(word))
    win[start:start + len(word)] += word[: CLIP - start] * rng.uniform(0.3, 1.5)
    return np.clip(win, -1, 1)


def make_dataset(pos, noise, neg_words, rng, per_pos=20):
    X, y = [], []
    for w in pos:
        for _ in range(per_pos):
            X.append(place(aug(w, rng), noise, rng)); y.append(1)
    n_pos = len(X)
    for _ in range(n_pos * 2):
        X.append(np.clip(bg(noise, rng), -1, 1)); y.append(0)
    for w in neg_words:
        for _ in range(per_pos):
            X.append(place(aug(w, rng), noise, rng)); y.append(0)
    for w in pos:   # половинки «Ке…» / «…ша» — срабатываем только на слово целиком
        for _ in range(per_pos // 3):
            part = w[: int(len(w) * rng.uniform(0.3, 0.5))] if rng.random() < 0.5 else w[int(len(w) * rng.uniform(0.5, 0.7)):]
            X.append(place(part, noise, rng)); y.append(0)
        for _ in range(per_pos // 4):   # начало звука после тишины (микрофон включился, ТВ заговорил)
            win = bg(noise, rng).copy()
            win[: int(rng.uniform(0.3, 1.5) * RATE)] = 0
            X.append(np.clip(win, -1, 1)); y.append(0)
        for _ in range(per_pos // 4):   # слово в начале окна: уже «прошло», второй раз не срабатываем
            win = bg(noise, rng).copy()
            win[: min(len(w), CLIP)] += w[:CLIP]
            X.append(np.clip(win, -1, 1)); y.append(0)
    return X, y


HARD_NAMES = [w for w in HARD_WORDS if w.lower() != "кеш"]
NEG_NAMES = [w for w in NEG_WORDS if w != "кеш"]


def train(pos_clips, neg_audio, hard, tts_pos=(), tts_neg=(), epochs=30, quiet=False):
    """-> (recall на проверочных записях, ложных срабатываний). Сохраняет HEAD_PATH."""
    import torch
    rng = np.random.default_rng(0)
    torch.manual_seed(0)
    fe = feature_extractor()
    pos_clips = list(pos_clips)
    random.Random(0).shuffle(pos_clips)
    cut = max(2, len(pos_clips) // 5)
    val_pos, train_pos = pos_clips[:cut], pos_clips[cut:]
    noise = np.concatenate(neg_audio) if neg_audio else rng.normal(0, 0.003, RATE * 40).astype(np.float32)
    split = int(len(noise) * 0.75)
    noise_tr, noise_va = noise[:split], noise[split:]
    # похожих слов мало (14) — учимся на всех, проверяем порог тоже на всех
    hard = list(hard)
    hard_va, hard_tr = [], hard

    X, y = make_dataset(train_pos * 2 + list(tts_pos), noise_tr, list(tts_neg) + hard_tr * 4, rng)
    if not quiet:
        print(f"🔢 Считаю признаки openWakeWord для {len(X)} окон...")
    X = torch.from_numpy(embed_clips(fe, X)).float()
    y = torch.tensor(y, dtype=torch.float32)

    torch.set_grad_enabled(True)
    net = build_head()
    opt = torch.optim.AdamW(net.parameters(), 1e-3, weight_decay=1e-2)
    # негативы важнее: лишнее срабатывание бесит сильнее, чем повторить «Кеша» (как в openWakeWord)
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor([0.5]))
    for ep in range(epochs):
        net.train()
        perm = torch.randperm(len(X))
        for i in range(0, len(perm), 128):
            b = perm[i:i + 128]
            opt.zero_grad()
            xb = X[b] + torch.randn_like(X[b]) * 0.05 * X.std()     # немного шума признаков
            loss_fn(net(xb).squeeze(1), y[b]).backward()
            opt.step()
        if not quiet and (ep + 1) % 10 == 0:
            print(f"   эпоха {ep + 1}/{epochs}")
    net.eval()

    # порог — по потоку на «чужом» фоне и похожих словах, как в train_wake.py
    def padded(w):
        return np.concatenate([bg(noise_va, rng, RATE), w * rng.uniform(0.5, 1.2), bg(noise_va, rng, RATE)])
    neg_streams = [noise_va] + [padded(w) for w in list(tts_neg) + hard] + \
                  [rng.normal(0, s, RATE * 10).astype(np.float32) for s in (0.0005, 0.005, 0.03)]
    neg_names = ["фон (проверочный)"] + [f"синтетика «{NEG_NAMES[i % len(NEG_NAMES)]}»" for i in range(len(tts_neg))] +                 [f"твоё «{w}»" for w in HARD_NAMES[:len(hard)]] + ["шум"] * 3
    neg_streaks = np.array([streak(stream_scores(net, fe, s)) for s in neg_streams])
    if not quiet:
        top = sorted(zip(neg_streaks, neg_names), reverse=True)[:4]
        print("   ближе всего к «Кеша»:", ", ".join(f"{n} {v:.3f}" for v, n in top))
    pos_best = np.array([streak(stream_scores(net, fe, padded(w))) for w in val_pos])
    thr = float(min(0.995, max(0.5, neg_streaks.max() + 0.03)))
    recall = float((pos_best >= thr).mean())
    false = int((neg_streaks >= thr).sum())
    WAKE_DIR.mkdir(parents=True, exist_ok=True)
    torch.save({"state": net.state_dict(), "threshold": thr}, HEAD_PATH)
    if not quiet:
        if hard_va:
            hv = [streak(stream_scores(net, fe, padded(w))) for w in hard_va]
            print(f"   похожие слова не из обучения: ложных {sum(s >= thr for s in hv)}/{len(hv)}")
        print(f"✅ Готово: порог {thr:.3f} | узнаёт «Кеша»: {recall * 100:.0f}% ({int(round(recall * len(val_pos)))}/{len(val_pos)}) | "
              f"ложных на {len(noise_va) / RATE / 60:.1f} мин фона: {false} -> {HEAD_PATH}")
        if recall < 0.8:
            print("⚠️ Узнаёт слабовато: запиши ещё (record — записи добавятся) и обучи заново.")
    return recall, false


def cmd_train():
    raw = load_wavs(POS_DIR)
    # пустые записи (не успел сказать / слишком тихо): пик почти на уровне шума микрофона
    pos = [trim_word(c) for c in raw if np.abs(c).max() >= 0.006]
    if len(pos) < len(raw):
        print(f"🔇 Пропускаю {len(raw) - len(pos)} пустых записей «Кеша» (тишина вместо слова)")
    if len(pos) < 10:
        sys.exit("❌ Мало записей слова. Сначала: python tools/train_oww.py record")
    neg = [c for c in load_wavs(NEG_DIR) if len(c) > CLIP]
    # «кеш» не негатив: в config это тоже слово-активатор, а звучит почти как «Кеша»
    hard = [trim_word(c) for i, c in enumerate(load_wavs(NEG_DIR, "hard_*.wav"))
            if HARD_WORDS[i % len(HARD_WORDS)].lower() != "кеш"]
    tts_pos, tts_neg = tts_samples()
    tts_neg = [w for i, w in enumerate(tts_neg) if NEG_WORDS[i % len(NEG_WORDS)] != "кеш"]
    print(f"📚 «Кеша» {len(pos)}, похожих слов {len(hard)}, фон {sum(map(len, neg)) / RATE:.0f} с, "
          f"синтетика {len(tts_pos)}+{len(tts_neg)}")
    train(pos, neg, hard, tts_pos, tts_neg)


def cmd_test(log_path=None):
    """Вживую, как в Кеше: openWakeWord + проверка GigaAM. Печатает пик каждого звука
    и решение; всё пишется в data/wake/test_scores.log."""
    import sounddevice as sd
    from voice.oww_wake import OwwWakeDetector, CHUNK
    from voice.gigaam_recognizer import GigaAMRecognizer
    from voice.listener import _gigaam_verify
    det = OwwWakeDetector(verify=_gigaam_verify(GigaAMRecognizer()))
    log = open(log_path or WAKE_DIR / "test_scores.log", "a", encoding="utf-8")
    print(f"👂 Порог {det.threshold:.3f}, с проверкой GigaAM от {det.soft_threshold}. "
          f"Говори «Кеша» и обычную речь. Ctrl+C — выход.")
    try:
        with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, channels=1, dtype="int16") as stream:
            while True:
                data, _ = stream.read(CHUNK)
                fired = det.step(np.frombuffer(bytes(data), dtype=np.int16))
                if det.last_event:
                    peak, how = det.last_event
                    line = f"{time.strftime('%H:%M:%S')} пик {peak:.3f} {how} {'✅ СЛЫШУ' if fired else '·'}"
                    print(line, flush=True)
                    log.write(line + "\n"); log.flush()
    except KeyboardInterrupt:
        pass


def cmd_threshold(value):
    import torch
    data = torch.load(HEAD_PATH, map_location="cpu", weights_only=True)
    data["threshold"] = float(value)
    torch.save(data, HEAD_PATH)
    print(f"✅ Порог {float(value):.3f} -> {HEAD_PATH}")


FAR_STYLES = [("издалека: отойди на 2–3 метра", 10), ("из другого угла комнаты, отвернувшись", 6),
              ("нечётко: лениво, бормоча, на выдохе", 8), ("с другой интонацией: вопросом, протяжно «Кеееша»", 6)]


def cmd_far():
    """Дописать трудные «Кеша»: издалека и нечётко. Окно 2.2 с — чтобы успеть подойти к слову."""
    i = len(list(POS_DIR.glob("*.wav")))
    for style, count in FAR_STYLES:
        input(f"➡️ Скажи «Кеша» {count} раз — {style}. Enter, чтобы начать…")
        for k in range(count):
            print(f"   {k + 1}/{count}: ", end="", flush=True)
            time.sleep(0.6)
            print("говори!", flush=True)
            save_wav(POS_DIR / f"pos_{i:03d}.wav", record_seconds(2.2))
            i += 1
    print("✅ Записано. Дальше: python tools/train_oww.py train")


def cmd_speech(sec=120):
    input(f"➡️ {sec} с обычной речи БЕЗ слова «Кеша»: читай книгу/статью или болтай. Enter…")
    save_wav(NEG_DIR / f"speech_{int(time.time())}.wav", record_seconds(sec))
    print("✅ Записано. Дальше: python tools/train_oww.py train")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "all"
    if action == "far":
        cmd_far()
    if action == "speech":
        cmd_speech(int(sys.argv[2]) if len(sys.argv) > 2 else 120)
    if action in ("record", "all"):
        cmd_record()
    if action in ("train", "all"):
        cmd_train()
    if action == "test":
        cmd_test()
    if action == "threshold":
        cmd_threshold(sys.argv[2])
