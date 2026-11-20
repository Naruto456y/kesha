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


def _shutdown(delay, max_wait, restart=False):
    time.sleep(delay)                      # дать озвучке начаться
    deadline = time.time() + max_wait
    while _speaking() and time.time() < deadline:
        time.sleep(0.1)
    for cb in list(_hooks):
        try:
            cb()
        except Exception as e:
            print(f"[exit] {e}", flush=True)
    if restart:
        _spawn_new_instance()
    os._exit(0)


def _spawn_new_instance():
    """Запустить новую Кешу с теми же аргументами; пауза нужна, чтобы старая успела отпустить мьютекс."""
    import subprocess
    import sys
    cmd = [sys.executable] + sys.argv
    launcher = ("import subprocess,sys,time;time.sleep(2);"
                "subprocess.Popen(sys.argv[1:],cwd=%r)" % os.getcwd())
    flags = 0x00000008 | 0x00000200 | 0x08000000     # DETACHED | NEW_PROCESS_GROUP | NO_WINDOW
    try:
        subprocess.Popen([sys.executable, "-c", launcher] + cmd, creationflags=flags, close_fds=True)
    except Exception as e:
        print(f"[restart] {e}", flush=True)


def request_exit(delay=1.5, max_wait=12.0, restart=False):
    """Закрыть программу после прощальной фразы (restart=True — и запустить заново).
    Повторный вызов ничего не делает."""
    global _requested
    with _lock:
        if _requested:
            return False
        _requested = True
    threading.Thread(target=_shutdown, args=(delay, max_wait, restart), daemon=True, name="exit").start()
    return True
