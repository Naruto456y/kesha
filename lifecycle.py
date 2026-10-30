"""
Завершение работы Кеши по команде «пока».

main.py регистрирует свою очистку через on_exit(); request_exit() ждёт, пока Кеша
договорит прощание, и закрывает программу целиком (голос, бот, сайт, окно, ngrok).
"""
import os
import threading
import time

_hooks = []
_requested = False
_lock = threading.Lock()


def on_exit(callback):
    if callback not in _hooks:
        _hooks.append(callback)


def _speaking():
    try:
        from voice.speaker import speaker
        return speaker.is_speaking or speaker.is_mic_blocked()
    except Exception:
        return False


def _shutdown(delay, max_wait):
    time.sleep(delay)                      # дать озвучке начаться
    deadline = time.time() + max_wait
    while _speaking() and time.time() < deadline:
        time.sleep(0.1)
    for cb in list(_hooks):
        try:
            cb()
        except Exception as e:
            print(f"[exit] {e}", flush=True)
    os._exit(0)


def request_exit(delay=1.5, max_wait=12.0):
    """Закрыть программу после прощальной фразы. Повторный вызов ничего не делает."""
    global _requested
    with _lock:
        if _requested:
            return False
        _requested = True
    threading.Thread(target=_shutdown, args=(delay, max_wait), daemon=True, name="exit").start()
    return True
