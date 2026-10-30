"""Общие хелперы для тестов Волны 1."""
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load(name):
    """Загрузить voice/<name>.py напрямую, не трогая voice/__init__.py."""
    spec = importlib.util.spec_from_file_location(f"w1_{name}", ROOT / "voice" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
