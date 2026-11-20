"""
Автоустановка зависимостей: `python main.py` на чистом компе сам всё ставит.

- Всё нужное уже стоит (мой ноут) → ничего не делаем.
- Не хватает пакетов и мы не в venv → создаём .venv в папке проекта, ставим туда
  requirements.txt и перезапускаем main.py уже из .venv.
- Уже в venv → ставим прямо в него.
- `python main.py --full` → дополнительно requirements-full.txt (нейросети, несколько ГБ).

Только стандартная библиотека: модуль работает до установки чего-либо.
"""
import hashlib
import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
STAMP = VENV / ".kesha-installed"     # хеш установленных requirements: поменялись — доставим

# модуль для импорта, без которого Кеша не стартует (по одному с каждого «слоя»)
REQUIRED = ["psutil", "dotenv", "requests", "keyboard", "mouse", "telegram", "fastapi", "uvicorn",
            "flask", "pygame", "gtts", "speech_recognition", "help_manager", "PyQt6", "sounddevice",
            "numpy", "rapidfuzz", "pywinauto"]


def missing_modules():
    importlib.invalidate_caches()
    return [m for m in REQUIRED if importlib.util.find_spec(m) is None]


def _req_files(full):
    return [ROOT / "requirements.txt"] + ([ROOT / "requirements-full.txt"] if full else [])


def _req_hash(full):
    h = hashlib.sha256()
    for f in _req_files(full):
        h.update(f.read_bytes())
    return h.hexdigest()


def _run(cmd):
    print(f"[setup] {' '.join(str(c) for c in cmd)}", flush=True)
    kw = {}
    if not (sys.stdout and sys.stdout.isatty()):      # pythonw: без мигающих консолей
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            sys.stdout.fileno()
            kw["stdout"] = kw["stderr"] = sys.stdout
        except Exception:
            kw["stdout"] = kw["stderr"] = subprocess.DEVNULL
    return subprocess.call([str(c) for c in cmd], **kw)


def _pip_install(python, full):
    req = _req_files(full)[-1]                        # full подтягивает базу через -r
    print(f"[setup] Ставлю зависимости из {req.name}"
          f"{' (нейросети, это надолго)' if full else ''}...", flush=True)
    code = 1
    for attempt in range(3):                          # школьная сеть / VPN рвут TLS — повторяем
        code = _run([python, "-m", "pip", "install", "--disable-pip-version-check",
                     "--retries", "10", "--timeout", "60", "-r", req])
        if code == 0:
            return True
        print(f"[setup] pip завершился с ошибкой {code} (попытка {attempt + 1} из 3)", flush=True)
    return False


def _give_up(missing):
    print(f"[setup] Не получилось поставить: {', '.join(missing)}.\n"
          "[setup] Скорее всего, сеть режет PyPI. Проверь интернет и запусти ещё раз: python main.py",
          flush=True)
    sys.exit(1)


def _venv_python():
    exe = "pythonw.exe" if Path(sys.executable).name.lower() == "pythonw.exe" else "python.exe"
    return VENV / "Scripts" / exe, VENV / "Scripts" / "python.exe"


def ensure(argv=None):
    """Вызвать в самом начале main.py. Может перезапустить main.py из .venv и выйти."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if os.environ.get("KESHA_NO_BOOTSTRAP"):
        return
    full = "--full" in argv
    if full:
        argv.remove("--full")
        sys.argv = [sys.argv[0]] + argv               # argparse в main.py про --full не знает
    in_venv = sys.prefix != sys.base_prefix
    missing = missing_modules()

    # ставим в текущий Python: мы в venv или у нас и так всё есть (свой ноут)
    if in_venv or not missing:
        if full or missing:
            _pip_install(sys.executable, full)
            still = missing_modules()
            if still:
                _give_up(still)
        return

    # чистый комп: всё ставим в .venv рядом с main.py и перезапускаемся оттуда
    print(f"[setup] Не хватает пакетов: {', '.join(missing)}. Готовлю окружение .venv...", flush=True)
    run_py, pip_py = _venv_python()
    if not pip_py.exists():
        if _run([sys.executable, "-m", "venv", VENV]):
            print("[setup] Не смог создать .venv — ставлю в текущий Python.", flush=True)
            if not _pip_install(sys.executable, full):
                _give_up(missing_modules())
            return
    want = _req_hash(full)
    have = STAMP.read_text(encoding="utf-8").strip() if STAMP.exists() else ""
    if want != have:
        if not _pip_install(pip_py, full):
            _give_up(missing)
        STAMP.write_text(want, encoding="utf-8")
    print("[setup] Запускаю Кешу из .venv", flush=True)
    sys.exit(subprocess.call([str(run_py), str(ROOT / "main.py")] + argv))
