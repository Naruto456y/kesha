"""
Уведомления Windows (волна 3): всплывающее окно, когда Кеша выполнила
фоновую задачу (напоминание, будильник, таймер, сообщение).
Не блокирует вызывающий поток. Без plyer — просто печать в консоль.
"""

import threading

from config import MEDIA_DIR

APP_NAME = "Кеша"
ICON = MEDIA_DIR / "Kesha.ico"

_listeners = []   # cb(title, message) — например, всплывашка в десктоп-UI
enabled = True


def add_listener(callback):
    if callback not in _listeners:
        _listeners.append(callback)


def _show(title, message, timeout):
    try:
        from plyer import notification
        notification.notify(
            title=title[:63], message=message[:255], app_name=APP_NAME,
            app_icon=str(ICON) if ICON.exists() else "", timeout=timeout,
        )
    except Exception as e:
        print(f"[notify] {title}: {message} (всплывашка недоступна: {e})")


def notify(title: str, message: str, timeout: int = 10):
    for cb in list(_listeners):
        try:
            cb(title, message)
        except Exception as e:
            print(f"[notify] ошибка подписчика: {e}")
    if enabled:
        threading.Thread(target=_show, args=(title, message, timeout),
                         daemon=True, name="notify").start()
