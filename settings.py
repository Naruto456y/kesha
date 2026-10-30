"""
Настройки, которые меняются голосом и переживают перезапуск: data/settings.json.
(Статичные настройки проекта — в config.py.)

    import settings
    settings.get("silent")            # -> False
    settings.set("theme", "light")    # сохранит и оповестит подписчиков
    settings.subscribe(cb)            # cb(key, value)
"""

import json
import os
import threading

from config import DATA_DIR

SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULTS = {
    "silent": False,         # тихий режим: не говорить вслух, только текст
    "language": "ru",        # ru | en — язык ответов и озвучки
    "voice": "male",         # male (eugene) | female (xenia) | robot (Silero, офлайн, ~0.3 с) | google (онлайн, 7–10 с)
    "theme": "dark",         # dark | light — тема десктоп-интерфейса
    "sounds": True,          # звуковые эффекты (пики/бупы)
    "floating_icon": True,   # плавающий значок реактора поверх окон
    "float_pos": None,       # [x, y] значка
}

_lock = threading.RLock()
_data = None
_subscribers = []
path = SETTINGS_FILE


def _load():
    global _data
    if _data is not None:
        return
    try:
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
        _data = loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError):
        _data = {}


def _save():
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError as e:
        print(f"[settings] не удалось сохранить: {e}")


def get(key):
    with _lock:
        _load()
        return _data.get(key, DEFAULTS.get(key))


def all_settings() -> dict:
    with _lock:
        _load()
        return {**DEFAULTS, **_data}


def set(key, value):
    with _lock:
        _load()
        if _data.get(key, DEFAULTS.get(key)) == value:
            return
        _data[key] = value
        _save()
    for cb in list(_subscribers):
        try:
            cb(key, value)
        except Exception as e:
            print(f"[settings] ошибка подписчика {cb}: {e}")


def subscribe(callback):
    if callback not in _subscribers:
        _subscribers.append(callback)


def unsubscribe(callback):
    if callback in _subscribers:
        _subscribers.remove(callback)


def use_file(new_path):
    """Переключиться на другой файл настроек (для тестов)."""
    global path, _data
    with _lock:
        path = new_path
        _data = None
