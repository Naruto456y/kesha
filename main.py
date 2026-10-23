"""Точка входа проекта Кеша."""
import ctypes
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "Yusuf.Kesha.VoiceAssistant.1.0"
    )
except Exception:
    pass

import argparse
import atexit
import os
import signal
import sys
import threading
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

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


def run_desktop():
    from desktop.main import start_desktop
    start_desktop()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--voice", action="store_true")
    p.add_argument("--telegram", action="store_true")
    p.add_argument("--alice", action="store_true")
    p.add_argument("--web", action="store_true")
    p.add_argument("--desktop", action="store_true")
    p.add_argument("--all", action="store_true")
    args = p.parse_args()

    no_flags = not any([
        args.voice, args.telegram, args.alice,
        args.web, args.desktop, args.all,
    ])
    run_all = args.all or no_flags

    import commands  # noqa: регистрация команд

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
                run_desktop()
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