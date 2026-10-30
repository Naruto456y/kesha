"""
Запись и обучение слова «Кеша» на твоём голосе.

    python tools/train_wake.py record     # ~5 минут: слово ×40 + обычная речь + фон
    python tools/train_wake.py train      # обучение (1–3 минуты) -> data/wake/model.pt
    python tools/train_wake.py test       # проверка вживую: говори, увидишь «СЛЫШУ»
    python tools/train_wake.py all        # record + train
"""
import random
import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from voice.local_wake import WAKE_DIR, MODEL_PATH, RATE, WINDOW, features, build_net  # noqa: E402

POS_DIR, NEG_DIR = WAKE_DIR / "pos", WAKE_DIR / "neg"
STYLES = [("обычно", 12), ("тихо", 8), ("громко", 8), ("быстро", 6), ("издалека (отойди от микрофона)", 6)]
# Похожие слова твоим голосом — главное, что учит модель не путать «Кеша» с «каша»/«Лёша»
HARD_WORDS = ["каша", "Лёша", "Паша", "Гоша", "Даша", "Миша", "кошка", "кеды", "кешью", "Кеш",
              "Наташа", "Кира", "кишка", "Яша"]
NEG_WORDS = ["каша", "кеш", "леша", "паша", "миша", "кеды", "привет", "открой браузер", "который час",
             "включи свет", "тише", "стоп", "пока", "да", "нет", "ну давай", "что там", "ладно"]


# ---------- wav ----------
def save_wav(path, pcm):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(np.asarray(pcm, dtype=np.int16).tobytes())


def load_wavs(folder, pattern="*.wav"):
    out = []
    for p in sorted(folder.glob(pattern)):
        with wave.open(str(p)) as w:
            out.append(np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0)
    return out


def trim_word(x, pad=0.08):
    """Обрезать тишину вокруг слова по энергии."""
    frame = 160
    n = len(x) // frame
    if n < 3:
        return x
    e = np.sqrt((x[: n * frame].reshape(n, frame) ** 2).mean(axis=1))
    idx = np.where(e > max(e.max() * 0.15, 0.003))[0]
    if len(idx) == 0:
        return x
    a, b = max(0, idx[0] * frame - int(pad * RATE)), min(len(x), (idx[-1] + 1) * frame + int(pad * RATE))
    return x[a:b]


# ---------- запись ----------
def record_seconds(sec):
    import sounddevice as sd
    data = sd.rec(int(sec * RATE), samplerate=RATE, channels=1, dtype="int16")
    sd.wait()
    return data[:, 0]


def cmd_record():
    print("🎙️ Запись. Говори в свой обычный микрофон на обычном расстоянии.\n")
    i = len(list(POS_DIR.glob("*.wav")))
    for style, count in STYLES:
        input(f"➡️ Сейчас скажи «Кеша» {count} раз — {style}. Enter, чтобы начать…")
        for k in range(count):
            print(f"   {k + 1}/{count}: ", end="", flush=True)
            time.sleep(0.5)
            print("говори!", flush=True)
            pcm = record_seconds(1.6)
            save_wav(POS_DIR / f"pos_{i:03d}.wav", pcm)
            i += 1
    input(f"\n➡️ Теперь {len(HARD_WORDS)} ПОХОЖИХ слов (НЕ «Кеша») — по одному, как показываю. Enter…")
    stamp = int(time.time())
    for k, word in enumerate(HARD_WORDS):
        print(f"   {k + 1}/{len(HARD_WORDS)}: скажи «{word}»… ", end="", flush=True)
        time.sleep(0.5)
        print("говори!", flush=True)
        save_wav(NEG_DIR / f"hard_{stamp}_{k:02d}.wav", record_seconds(1.6))
    input("\n➡️ Теперь ОБЫЧНАЯ РЕЧЬ без слова «Кеша»: читай вслух что угодно (новости, книгу) 60 секунд. Enter…")
    save_wav(NEG_DIR / f"speech_{int(time.time())}.wav", record_seconds(60))
    input("➡️ И 20 секунд фона: включи видео/музыку, как обычно. Enter…")
    save_wav(NEG_DIR / f"background_{int(time.time())}.wav", record_seconds(20))
    print(f"\n✅ Записано. Дальше: python tools/train_wake.py train")


# ---------- обучение ----------
def tts_samples():
    """Синтетика Silero: слово «Кеша» разными голосами (+ похожие слова как негативы)."""
    try:
        from voice.tts_engines import load_silero
        from scipy.signal import resample_poly
        model = load_silero()
    except Exception as e:
        print(f"   (Silero недоступна, без синтетики: {e})")
        return [], []

    def say(text, speaker):
        a = model.apply_tts(text=text, speaker=speaker, sample_rate=48000).numpy()
        return resample_poly(a, 1, 3).astype(np.float32)

    pos = [trim_word(say(w, s)) for s in ("xenia", "aidar", "baya", "kseniya", "eugene") for w in ("Кеша", "кеша")]
    neg = [trim_word(say(w, s)) for s in ("xenia", "aidar", "eugene") for w in NEG_WORDS]
    return pos, neg


def stretch(word, rng):
    """Темп ±12%: «Кеша» быстрее/медленнее, чем на записи."""
    from scipy.signal import resample_poly
    k = int(rng.integers(88, 113))
    return resample_poly(word, k, 100).astype(np.float32) if k != 100 else word


def bg_window(noise, rng):
    """Окно фона: твоя речь/фон из записей, либо тишина/тихий шум микрофона разной громкости."""
    if rng.random() < 0.7:
        return noise[rng.integers(0, len(noise) - WINDOW):][:WINDOW] * rng.uniform(0.3, 2.0)
    return rng.normal(0, 10 ** rng.uniform(-3.7, -1.7), WINDOW).astype(np.float32)


def place(word, noise, rng):
    """Слово в случайном месте 1-секундного окна поверх фона."""
    word = word[: int(WINDOW * 0.95)]
    win = bg_window(noise, rng).copy()
    start = rng.integers(0, WINDOW - len(word) + 1)
    win[start : start + len(word)] += word * rng.uniform(0.3, 1.5)
    return np.clip(win, -1, 1)


def make_dataset(pos_words, noise, neg_words, rng, per_pos=25):
    """Позитивы: слово целиком. Негативы: фон (в т.ч. тишина), похожие слова,
    половинки «Кеша» («ке…», «…ша») — чтобы срабатывать только на всё слово."""
    X, y = [], []
    for w in pos_words:
        for _ in range(per_pos):
            X.append(features(place(stretch(w, rng), noise, rng))); y.append(1)
    n_pos = len(X)
    for _ in range(n_pos * 3):
        X.append(features(np.clip(bg_window(noise, rng), -1, 1))); y.append(0)
    for w in neg_words:
        for _ in range(per_pos):
            X.append(features(place(stretch(w, rng), noise, rng))); y.append(0)
    for w in pos_words:
        for _ in range(per_pos // 3):
            part = w[: int(len(w) * rng.uniform(0.3, 0.5))] if rng.random() < 0.5 else w[int(len(w) * rng.uniform(0.5, 0.7)):]
            X.append(features(place(part, noise, rng))); y.append(0)
    return X, y


def spec_augment(x, gen):
    """Маски по частоте и времени (SpecAugment) — модель не цепляется за одну деталь."""
    import torch
    x = x.clone()
    n, _, f, t = x.shape
    for i in range(n):
        if torch.rand(1, generator=gen) < 0.5:
            f0 = int(torch.randint(0, f - 6, (1,), generator=gen)); x[i, :, f0:f0 + int(torch.randint(1, 7, (1,), generator=gen))] = 0
            t0 = int(torch.randint(0, t - 10, (1,), generator=gen)); x[i, :, :, t0:t0 + int(torch.randint(1, 11, (1,), generator=gen))] = 0
    return x


def streak(scores, hits_needed=2):
    """Лучший «пробег»: минимум из hits_needed окон подряд — с этим сравнивается порог."""
    if len(scores) < hits_needed:
        return 0.0
    return float(max(min(scores[i:i + hits_needed]) for i in range(len(scores) - hits_needed + 1)))


def cmd_train(epochs=20, quiet=False):
    import torch
    from voice.local_wake import ARCH, stream_scores
    rng = np.random.default_rng(0)
    torch.manual_seed(0)
    pos_clips = [trim_word(c) for c in load_wavs(POS_DIR)]
    neg_audio = [c for c in load_wavs(NEG_DIR) if len(c) > WINDOW * 2]
    hard = [trim_word(c) for c in load_wavs(NEG_DIR, "hard_*.wav")]   # «каша», «Лёша» твоим голосом
    if len(pos_clips) < 10:
        sys.exit("❌ Мало записей слова. Сначала: python tools/train_wake.py record")
    tts_pos, tts_neg = tts_samples()
    torch.set_grad_enabled(True)          # Silero выключает градиенты глобально
    random.Random(0).shuffle(pos_clips)
    cut = max(2, len(pos_clips) // 5)
    val_pos, train_pos = pos_clips[:cut], pos_clips[cut:]
    # фон делим: 75% — обучение, 25% — проверка ложных срабатываний на «чужом» отрезке
    noise = np.concatenate(neg_audio) if neg_audio else rng.normal(0, 0.003, RATE * 40).astype(np.float32)
    split = int(len(noise) * 0.75)
    noise_tr, noise_va = noise[:split], noise[split:]
    hard_va, hard_tr = hard[::4], [w for i, w in enumerate(hard) if i % 4]
    print(f"📚 Твоих записей: «Кеша» {len(pos_clips)} (проверочных {cut}), похожих слов {len(hard)}, "
          f"фон {len(noise) / RATE:.0f} с, синтетика: {len(tts_pos)}+{len(tts_neg)}")

    X, y = make_dataset(train_pos * 2 + tts_pos, noise_tr, tts_neg + hard_tr * 4, rng)
    X, y = torch.stack(X), torch.tensor(y, dtype=torch.float32)

    net = build_net()
    opt = torch.optim.AdamW(net.parameters(), 2e-3, weight_decay=1e-3)
    steps = epochs * ((len(X) + 63) // 64)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-3, total_steps=steps)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    gen = torch.Generator().manual_seed(0)
    for ep in range(epochs):
        net.train()
        perm = torch.randperm(len(X))
        for i in range(0, len(perm), 64):
            b = perm[i : i + 64]
            opt.zero_grad()
            loss_fn(net(spec_augment(X[b], gen)).squeeze(1), y[b]).backward()
            opt.step(); sched.step()
        if not quiet and (ep + 1) % 5 == 0:
            print(f"   эпоха {ep + 1}/{epochs}")
    net.eval()

    # Порог — по потоку, как в живой работе: выше любого «пробега» на проверочном фоне
    # и похожих словах, но так, чтобы твои проверочные «Кеша» проходили.
    def padded(w):
        return np.concatenate([bg_window(noise_va, rng)[: RATE // 2], w * rng.uniform(0.5, 1.2), bg_window(noise_va, rng)[: RATE // 2]])
    # (половинки «Ке…» — только в обучении: в калибровке они задирают порог и режут узнавание)
    neg_streams = [noise_va] + [padded(w) for w in tts_neg + hard] + \
                  [rng.normal(0, s, RATE * 10).astype(np.float32) for s in (0.0005, 0.005, 0.03)]
    neg_streaks = np.array([streak(stream_scores(net, s)) for s in neg_streams])
    pos_best = np.array([streak(stream_scores(net, padded(w))) for w in val_pos])
    # нижняя граница 0.6: похожие слова, которых не было в записи, дают оценки повыше проверочных
    thr = float(min(0.995, max(0.6, neg_streaks.max() + 0.03)))
    if hard_va:
        hv = [streak(stream_scores(net, padded(w))) for w in hard_va]
        print(f"   похожие слова не из обучения: ложных {sum(s >= thr for s in hv)}/{len(hv)}")
    recall = float((pos_best >= thr).mean())
    false = int((neg_streaks >= thr).sum())
    far_min = len(noise_va) / RATE / 60
    WAKE_DIR.mkdir(parents=True, exist_ok=True)
    torch.save({"state": net.state_dict(), "threshold": thr, "arch": ARCH}, MODEL_PATH)
    print(f"✅ Готово: порог {thr:.3f} | узнаёт твоё «Кеша»: {recall * 100:.0f}% ({int(recall * len(val_pos))}/{len(val_pos)}) | "
          f"ложных на {far_min:.1f} мин фона и {len(tts_neg) + len(hard)} похожих словах: {false} -> {MODEL_PATH}")
    if not hard:
        print("💡 Записей похожих слов нет — запиши заново (record), они сильно снижают ложные срабатывания.")
    if recall < 0.8:
        print("⚠️ Узнаёт слабовато: запиши ещё (python tools/train_wake.py record — записи добавятся) и обучи заново.")
    return recall, false


def cmd_test():
    from voice.local_wake import LocalWakeDetector
    det = LocalWakeDetector()
    print(f"👂 Порог {det.threshold:.2f}. Говори «Кеша» (и всякую другую речь). Ctrl+C — выход.")
    try:
        while True:
            if det.wait_for_wake():
                print(time.strftime("%H:%M:%S"), "✅ СЛЫШУ «Кеша»")
                time.sleep(1.0)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "all"
    if action in ("record", "all"):
        cmd_record()
    if action in ("train", "all"):
        cmd_train()
    if action == "test":
        cmd_test()
