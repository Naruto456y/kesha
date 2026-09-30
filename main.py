"""Точка входа проекта Кеша."""
import argparse, threading, sys


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

    import commands  # noqa: регистрация команд

    threads = []
    if args.voice or args.all:
        threads.append(threading.Thread(target=run_voice, daemon=True, name="voice"))
    if args.telegram or args.all:
        threads.append(threading.Thread(target=run_telegram, daemon=True, name="telegram"))
    if args.alice or args.all:
        threads.append(threading.Thread(target=run_alice, daemon=True, name="alice"))
    if args.web or args.all:
        threads.append(threading.Thread(target=run_website, daemon=True, name="web"))

    for t in threads:
        t.start()
        print("[main] Запущено:", t.name)

    if args.desktop or args.all:
        run_desktop()
    else:
        for t in threads:
            t.join()


if __name__ == "__main__":
    sys.exit(main() or 0)
