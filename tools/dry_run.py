"""
Сухой прогон фраз: какая команда ловит каждую. Ничего не запускается и не нажимается —
программы, клавиатура, мышь, интернет, выключение ПК заглушены; данные — во временной папке.

    python tools/dry_run.py                     # фразы из tools/phrases.txt
    python tools/dry_run.py мои_фразы.txt
    python tools/dry_run.py --only-unknown      # только то, что ушло бы в GigaChat

В конце — сколько фраз поняты локально, а сколько ушли бы в GigaChat.
"""
import os
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")

# Фразы, которые трогают железо даже через заглушки (свет по сети, выключение) — не гоняем
SKIP = ("свет", "ухожу", "ушёл", "ушел", "иду спать", "пойду спать", "хаос", "селфи", "камер",
        "позвони", "блютуз", "bluetooth")


def _stub_everything(tmp):
    noop = lambda *a, **k: None   # noqa: E731
    os.startfile = noop
    os.system = lambda *a, **k: 0
    webbrowser.open = webbrowser.open_new_tab = noop
    import keyboard
    import mouse
    for n in ("send", "write", "press", "release", "press_and_release"):
        setattr(keyboard, n, noop)
    for n in ("move", "click", "right_click", "wheel", "press", "release"):
        setattr(mouse, n, noop)
    import AppOpener
    AppOpener.open = AppOpener.close = noop
    import klog, notify, settings
    klog.set_path(tmp / "kesha.log")
    notify.enabled = False
    settings.use_file(tmp / "settings.json")
    import core
    core.ai_ask = lambda *a, **k: "(GigaChat)"
    import commands
    import features  # noqa: F401
    from features import reminders, notes, stats, agenda, utilities
    reminders.store = reminders.ReminderStore(tmp / "reminders.json")
    notes.store = notes.NotesStore(tmp / "notes.json")
    stats.use_db(tmp / "stats.db")
    agenda.use_file(tmp / "calendar.json")
    agenda.ics_urls = []
    commands._set_volume = lambda *a, **k: True
    commands.PIL_AVAILABLE = False                 # скриншоты не сохраняем
    commands._gig = None
    commands.GIGACHAT_AVAILABLE = False
    utilities.set_mute = lambda on: True
    from features import claude_agent
    claude_agent.ENABLED = False                   # без Клода и выученных команд
    import lifecycle
    lifecycle.request_exit = lambda *a, **k: True      # «пока» не должно закрывать прогон
    import voice
    voice.say = noop
    import requests
    def offline(*a, **k):
        raise RuntimeError("сухой прогон: без интернета")
    requests.get = requests.post = offline
    # subprocess — последним: asyncio и прочие импорты выше им пользуются
    subprocess.Popen = lambda *a, **k: type("P", (), {"wait": noop, "pid": 0,
                                                       "communicate": lambda s, *a, **k: (b"", b"")})()
    subprocess.run = lambda *a, **k: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    subprocess.call = subprocess.check_call = lambda *a, **k: 0
    return core


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only_unknown = "--only-unknown" in sys.argv
    src = Path(args[0]) if args else ROOT / "tools" / "phrases.txt"
    phrases = [l.strip() for l in src.read_text(encoding="utf-8").splitlines()
               if l.strip() and not l.lstrip().startswith("#")]
    core = _stub_everything(Path(tempfile.mkdtemp(prefix="kesha_dry_")))
    names = []
    core.on_command(lambda s, n, t, r: names.append(n))

    unknown = skipped = 0
    for p in phrases:
        if any(w in p.lower() for w in SKIP):
            skipped += 1
            continue
        names.clear()
        try:
            r = core.handle_command(p, source="app", ai=True)
        except Exception as e:
            r = f"ОШИБКА {e}"
        n = names[-1] if names else "-"
        if n == "ai":
            unknown += 1
        if not only_unknown or n == "ai":
            mark = "🤖" if n == "ai" else "✅"
            print(f"{mark} {n:20} | {p:45} | {str(r).splitlines()[0][:60] if r else ''}")
    done = len(phrases) - skipped
    print(f"\nИтого: {done} фраз, поняты локально {done - unknown}, ушли бы в GigaChat {unknown}"
          + (f", пропущено опасных {skipped}" if skipped else ""))


if __name__ == "__main__":
    main()
