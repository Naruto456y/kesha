"""
База голоса: Кеша сохраняет то, что ей сказали, — для дообучения слова «Кеша»,
узнавания голоса хозяина и проверки распознавания.

    data/voice_db/index.db            sqlite: когда, что распознано, вид записи, громкость
    data/voice_db/2026-11/*.wav       сами записи (16 кГц, моно, int16)

Виды записей (kind):
    command   фраза, сказанная Кеше (после «Кеша» или горячей клавиши)
    wake_pos  1.8 с со словом «Кеша», подтверждённым GigaAM
    wake_neg  детектор сработал, а GigaAM «Кеша» не услышал — трудный пример «не Кеша»

Фоновую речь без «Кеша» не пишем: там видео и чужие разговоры.
Запись идёт своим потоком, голосовой цикл не тормозит. Старое удаляется, когда база
больше VOICE_DB_MAX_MB. Экспорт в обучение слова: python tools/voice_db.py export
"""
import queue
import sqlite3
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

import settings
from config import DATA_DIR

RATE = 16000
DB_DIR = DATA_DIR / "voice_db"
MAX_MB = 1500                 # больше — удаляем самые старые записи
NEG_PER_HOUR = 30             # «не Кеша» при включённом видео сыплются десятками — ограничиваем
MIN_SEC = 0.3
KINDS = ("command", "wake_pos", "wake_neg")

_q = queue.Queue(maxsize=64)
_worker = None
_lock = threading.Lock()
_neg_times = []
_dir = DB_DIR


def use_dir(path):
    """Тесты: писать базу во временную папку."""
    global _dir
    drain()
    _dir = Path(path)


def enabled() -> bool:
    return bool(settings.get("voice_db"))


def _connect():
    _dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(_dir / "index.db")
    con.execute("""CREATE TABLE IF NOT EXISTS clips (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, path TEXT, text TEXT,
        dur REAL, db REAL, score REAL, bytes INTEGER)""")
    return con


def _level_db(pcm: np.ndarray) -> float:
    if not len(pcm):
        return -120.0
    rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2))) + 1e-9
    return round(20 * float(np.log10(rms / 32768)), 1)


def _write(item):
    kind, pcm, text, score, ts = item
    when = datetime.fromtimestamp(ts)
    folder = _dir / when.strftime("%Y-%m")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{when.strftime('%d_%H%M%S')}_{int(ts * 1000) % 1000:03d}_{kind}.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    con = _connect()
    try:
        con.execute("INSERT INTO clips (ts, kind, path, text, dur, db, score, bytes) VALUES (?,?,?,?,?,?,?,?)",
                    (ts, kind, str(path.relative_to(_dir)), text, round(len(pcm) / RATE, 2),
                     _level_db(pcm), score, path.stat().st_size))
        con.commit()
        _prune(con)
    finally:
        con.close()


def _prune(con):
    total = con.execute("SELECT COALESCE(SUM(bytes), 0) FROM clips").fetchone()[0]
    limit = MAX_MB * 1024 * 1024
    while total > limit:
        row = con.execute("SELECT id, path, bytes FROM clips ORDER BY ts LIMIT 1").fetchone()
        if not row:
            break
        try:
            (_dir / row[1]).unlink()
        except OSError:
            pass
        con.execute("DELETE FROM clips WHERE id = ?", (row[0],))
        con.commit()
        total -= row[2] or 0


def _run():
    while True:
        item = _q.get()
        try:
            _write(item)
        except Exception as e:
            print(f"[voicedb] запись не сохранена: {e}")
        finally:
            _q.task_done()


def save(kind: str, audio, text: str = "", score: float = None) -> bool:
    """audio — bytes (PCM int16) или np.int16. Возвращает True, если запись поставлена в очередь."""
    global _worker
    if kind not in KINDS or not enabled():
        return False
    try:
        pcm = np.frombuffer(audio, dtype=np.int16) if isinstance(audio, (bytes, bytearray))             else np.asarray(audio, dtype=np.int16)
    except (ValueError, TypeError):
        return False                # не звук (обрезанный буфер) — базе он не нужен
    if len(pcm) < MIN_SEC * RATE:
        return False
    now = time.time()
    with _lock:
        if kind == "wake_neg":
            _neg_times[:] = [t for t in _neg_times if now - t < 3600]
            if len(_neg_times) >= NEG_PER_HOUR:
                return False
            _neg_times.append(now)
        if _worker is None:
            _worker = threading.Thread(target=_run, daemon=True, name="voicedb")
            _worker.start()
    try:
        _q.put_nowait((kind, pcm.copy(), text or "", score, now))
        return True
    except queue.Full:
        return False


def drain():
    """Дождаться записи всего, что в очереди (тесты, выход)."""
    if _worker is not None:
        _q.join()


def rows(kind=None, limit=None):
    """[(ts, kind, полный путь, text, dur, db, score)] от новых к старым."""
    if not (_dir / "index.db").exists():
        return []
    con = _connect()
    try:
        sql = "SELECT ts, kind, path, text, dur, db, score FROM clips"
        args = []
        if kind:
            sql += " WHERE kind = ?"
            args.append(kind)
        sql += " ORDER BY ts DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [(r[0], r[1], str(_dir / r[2]), *r[3:]) for r in con.execute(sql, args)]
    finally:
        con.close()


def stats() -> dict:
    """{'command': (штук, секунд), ..., 'mb': размер}"""
    out = {k: (0, 0.0) for k in KINDS}
    if not (_dir / "index.db").exists():
        return {**out, "mb": 0.0}
    con = _connect()
    try:
        for kind, n, sec in con.execute("SELECT kind, COUNT(*), COALESCE(SUM(dur), 0) FROM clips GROUP BY kind"):
            out[kind] = (n, float(sec))
        size = con.execute("SELECT COALESCE(SUM(bytes), 0) FROM clips").fetchone()[0]
    finally:
        con.close()
    return {**out, "mb": round(size / 1024 / 1024, 1)}
