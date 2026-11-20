"""База голоса Кеши (data/voice_db): что накопилось и как пустить это в обучение.

    python tools/voice_db.py            сколько записей каждого вида
    python tools/voice_db.py list 20    последние 20 записей с текстом
    python tools/voice_db.py export     подтверждённые «Кеша» -> data/wake/pos, трудные «не Кеша»
                                        -> data/wake/neg; потом: python tools/train_oww.py train
"""
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from voice import voicedb  # noqa: E402

NAMES = {"command": "команды Кеше", "wake_pos": "слово «Кеша»", "wake_neg": "не «Кеша» (ложные срабатывания)"}
EXPORT_MARK = voicedb.DB_DIR / ".exported"     # время последнего экспорта: дважды одно не выгружаем


def _read(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def cmd_stats():
    s = voicedb.stats()
    for kind, title in NAMES.items():
        n, sec = s[kind]
        print(f"{title:36} {n:5} шт.  {sec / 60:6.1f} мин")
    print(f"всего на диске: {s['mb']} МБ (предел {voicedb.MAX_MB} МБ)")


def cmd_list(n=20):
    for ts, kind, path, text, dur, db, score in voicedb.rows(limit=n):
        print(f"{datetime.fromtimestamp(ts):%d.%m %H:%M:%S}  {kind:8} {dur:4.1f} с {db:6.1f} dB  {text!r}")


def cmd_export():
    from voice.oww_wake import WAKE_DIR
    since = float(EXPORT_MARK.read_text()) if EXPORT_MARK.exists() else 0.0
    pos = [r for r in voicedb.rows("wake_pos") if r[0] > since]
    neg = [r for r in voicedb.rows("wake_neg") if r[0] > since]
    pos_dir, neg_dir = WAKE_DIR / "pos", WAKE_DIR / "neg"
    pos_dir.mkdir(parents=True, exist_ok=True)
    neg_dir.mkdir(parents=True, exist_ok=True)
    for ts, _kind, path, *_ in pos:
        out = pos_dir / f"pos_auto_{int(ts)}.wav"
        out.write_bytes(Path(path).read_bytes())
    if neg:
        audio = np.concatenate([_read(r[2]) for r in neg])
        with wave.open(str(neg_dir / f"auto_neg_{int(time.time())}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(voicedb.RATE)
            w.writeframes(audio.tobytes())
    EXPORT_MARK.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_MARK.write_text(str(time.time()))
    print(f"В обучение добавлено: «Кеша» {len(pos)}, не «Кеша» {len(neg)} ({sum(r[4] for r in neg):.0f} с).")
    print("Проверь на слух data/wake/pos/pos_auto_*.wav: там должно быть только твоё «Кеша».")
    print("Дальше: python tools/train_oww.py train")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if arg == "list":
        cmd_list(int(sys.argv[2]) if len(sys.argv) > 2 else 20)
    elif arg == "export":
        cmd_export()
    else:
        cmd_stats()
