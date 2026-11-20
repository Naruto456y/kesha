"""Точка входа проекта Кеша."""
import ctypes
# один AppUserModelID с ярлыком «Кеша» (tools/install_shortcuts.py): закреплённый значок
# и окно Кеши — одна кнопка на панели задач, с логотипом Кеши, а не питона
APP_ID = "Yusuf.Kesha.VoiceAssistant.1.0"
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except Exception:
    pass

import argparse
import atexit
import os
import signal
import sys
import threading
import time

# Kesha.exe запускает pythonw — консоли нет, sys.stdout = None. Пишем вывод в logs/console.log.
if sys.stdout is None or sys.stderr is None:
    _log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(_log_dir, exist_ok=True)
    _path = os.path.join(_log_dir, "console.log")
    if os.path.exists(_path) and os.path.getsize(_path) > 5_000_000:
        os.replace(_path, _path + ".old")
    # "a", не "w": вторая копия (клик по значку, когда Кеша уже работает) не затирает лог первой
    _console = open(_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or _console
    sys.stderr = sys.stderr or _console

# Консоль Windows по умолчанию cp1251: print со смайликом (help_manager печатает «✅»)
# падал с UnicodeEncodeError, и GigaChat в commands.py молча отключался.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# чистый комп: создать .venv, поставить зависимости и перезапуститься оттуда (--full — с нейросетями)
import bootstrap
bootstrap.ensure()

import psutil


_shutdown_done = False


def _cleanup():
    global _shutdown_done
    if _shutdown_done:
        return
    _shutdown_done = True

    print("\n[main] Завершение, убиваю дочерние процессы...", flush=True)
    try:
        me = psutil.Process()
    except Exception as e:
        print(f"[main] psutil ошибка: {e}", flush=True)
        return

    children = me.children(recursive=True)
    if not children:
        print("[main] Дочерних процессов нет", flush=True)
        return

    for ch in children:
        try:
            print(f"[main]   → terminate {ch.name()} (pid={ch.pid})", flush=True)
            ch.terminate()
        except Exception:
            pass

    _, alive = psutil.wait_procs(children, timeout=3)

    for p in alive:
        try:
            print(f"[main]   → kill {p.name()} (pid={p.pid})", flush=True)
            p.kill()
        except Exception:
            pass

    print("[main] Всё завершено.", flush=True)


def _on_signal(signum, frame):
    print(f"\n[main] Сигнал {signum}", flush=True)
    _cleanup()
    sys.exit(0)


atexit.register(_cleanup)
import lifecycle
lifecycle.on_exit(_cleanup)       # «Кеша, пока» закрывает всё и убивает ngrok
signal.signal(signal.SIGINT, _on_signal)
signal.signal(signal.SIGTERM, _on_signal)
if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, _on_signal)


def run_voice():
    from voice import start_voice_loop
    start_voice_loop()


def run_telegram():
    from telegram_bot import start_bot
    start_bot()


def run_alice():
    from alice_skill import start_alice
    start_alice()


def run_website():
    from website import start_website
    start_website()


def run_desktop(minimized=False):
    # torch и onnxruntime грузим ДО Qt: Qt 6.9 приносит свой старый msvcp140.dll, и если он
    # загрузится первым, torch и GigaAM падают с WinError 1114 (голос уходит на Google)
    for mod in ("torch", "onnxruntime"):
        try:
            __import__(mod)
        except Exception as e:
            print(f"[main] {mod} не загрузился: {e}")
    from desktop.main import start_desktop
    start_desktop(minimized)


def _show_running_window():
    """Клик по значку, когда Кеша уже работает: развернуть и показать её окно."""
    try:
        from config import DESKTOP_TITLE
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, DESKTOP_TITLE)
        if hwnd:
            user32.ShowWindow(hwnd, 9)                          # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--voice", action="store_true")
    p.add_argument("--telegram", action="store_true")
    p.add_argument("--alice", action="store_true")
    p.add_argument("--web", action="store_true")
    p.add_argument("--desktop", action="store_true")
    p.add_argument("--all", action="store_true")
    p.add_argument("--minimized", action="store_true", help="окно свернуть (автозагрузка)")
    args = p.parse_args()

    no_flags = not any([
        args.voice, args.telegram, args.alice,
        args.web, args.desktop, args.all,
    ])
    run_all = args.all or no_flags

    # одна Кеша на ПК: две слушают один микрофон (команды по два раза) и ловят Telegram Conflict
    global _instance_mutex, _shutdown_done
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _instance_mutex = kernel32.CreateMutexW(None, False, "Global\\KeshaAssistant")
    if ctypes.get_last_error() == 183:                        # ERROR_ALREADY_EXISTS
        print("[main] Кеша уже запущена — вторую копию не запускаю, показываю окно.")
        _show_running_window()
        _shutdown_done = True                                 # у копии нечего чистить
        sys.exit(1)

    import commands  # noqa: регистрация команд (и фич волн 3–5)
    import features
    features.start_background()   # напоминания, будильники, таймеры

    if args.telegram or run_all:
        # импорт в главном потоке: параллельный импорт из потоков вешал бота на старте
        import telegram_bot.bot  # noqa: F401

    threads = []
    if args.voice or run_all:
        threads.append(threading.Thread(target=run_voice, daemon=True, name="voice"))
    if args.telegram or run_all:
        threads.append(threading.Thread(target=run_telegram, daemon=True, name="telegram"))
    if args.alice or run_all:
        threads.append(threading.Thread(target=run_alice, daemon=True, name="alice"))
    if args.web or run_all:
        threads.append(threading.Thread(target=run_website, daemon=True, name="web"))

    for t in threads:
        t.start()
        print(f"[main] Запущено: {t.name}", flush=True)

    try:
        if args.desktop or run_all:
            try:
                run_desktop(args.minimized)
            except ImportError as e:
                print(f"[main] Desktop недоступен ({e}) — работаю без GUI", flush=True)
                while True:
                    time.sleep(0.5)
        else:
            while True:
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("[main] Ctrl+C", flush=True)
    finally:
        _cleanup()


if __name__ == "__main__":
    main()