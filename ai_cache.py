"""
Кэш ответов GigaChat (волна 2): одинаковый вопрос не тратит токены дважды.
Хранится в JSON-файле, переживает перезапуск. Записи живут AI_CACHE_TTL секунд.
"""

import json
import os
import threading
import time

from config import AI_CACHE_FILE, AI_CACHE_MAX, AI_CACHE_TTL


class AICache:
    def __init__(self, path=AI_CACHE_FILE, ttl=AI_CACHE_TTL, max_items=AI_CACHE_MAX):
        self.path = path
        self.ttl = ttl
        self.max_items = max_items
        self._lock = threading.Lock()
        self._data = None   # key -> {"v": str, "ts": float}, грузим лениво

    def _load(self):
        if self._data is not None:
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self._data = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            self._data = {}

    def _save(self):
        tmp = f"{self.path}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError as e:
            print(f"[ai_cache] не удалось сохранить: {e}")

    def get(self, key: str) -> "str | None":
        if not key:
            return None
        with self._lock:
            self._load()
            item = self._data.get(key)
            if item is None:
                return None
            if time.time() - item["ts"] > self.ttl:
                del self._data[key]
                return None
            return item["v"]

    def put(self, key: str, value: str):
        if not key or not value:
            return
        with self._lock:
            self._load()
            self._data[key] = {"v": value, "ts": time.time()}
            if len(self._data) > self.max_items:
                oldest = sorted(self._data, key=lambda k: self._data[k]["ts"])
                for k in oldest[: len(self._data) - self.max_items]:
                    del self._data[k]
            self._save()

    def clear(self):
        with self._lock:
            self._data = {}
            self._save()


cache = AICache()
