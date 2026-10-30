"""
Защита от опасных команд (волна 3): чёрный/белый список приложений,
запрещённые сочетания клавиш, опасный текст для «напечатай», системные папки.

Списки — в config.py (SECURITY_*). Каждая функция возвращает причину отказа
(строку) или None, если всё в порядке.
"""

import os
import re
from pathlib import Path

from config import (SECURITY_BLOCKED_APPS, SECURITY_ALLOWED_APPS,
                    SECURITY_BLOCKED_KEYS, SECURITY_BLOCKED_TEXT)

_TEXT_RE = re.compile("|".join(SECURITY_BLOCKED_TEXT), re.I) if SECURITY_BLOCKED_TEXT else None


def _norm(s: str) -> str:
    return " ".join(s.lower().replace("ё", "е").split())


def _mentions(text: str, name: str) -> bool:
    return re.search(r"(?<![\w])" + re.escape(_norm(name)) + r"(?![\w])", text) is not None


def check_app(name: str) -> "str | None":
    """Можно ли открыть приложение. Белый список (если задан) важнее чёрного."""
    t = _norm(name)
    if not t:
        return None
    for bad in SECURITY_BLOCKED_APPS:
        if _mentions(t, bad):
            return f"«{bad}» в чёрном списке"
    if SECURITY_ALLOWED_APPS and not any(_mentions(t, ok) for ok in SECURITY_ALLOWED_APPS):
        return f"«{name}» нет в белом списке"
    return None


def check_keys(combo: str) -> "str | None":
    """«win+r» открывает «Выполнить» — оттуда можно запустить что угодно."""
    keys = "+".join(k.strip() for k in _norm(combo).replace(" ", "+").split("+") if k.strip())
    for bad in SECURITY_BLOCKED_KEYS:
        if keys == bad or keys.endswith("+" + bad) or keys.startswith(bad + "+"):
            return f"сочетание {bad} запрещено"
    return None


def check_text(text: str) -> "str | None":
    """Текст для «напечатай» не должен быть командой удаления/форматирования."""
    if _TEXT_RE is not None:
        m = _TEXT_RE.search(text)
        if m:
            return f"текст похож на опасную команду ({m.group(0).strip()})"
    return None


def _protected_roots():
    env = os.environ
    roots = [env.get("SystemRoot", r"C:\Windows"), env.get("ProgramFiles", r"C:\Program Files"),
             env.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
             env.get("ProgramData", r"C:\ProgramData")]
    return [Path(r).resolve() for r in roots if r]


def is_protected_path(path) -> bool:
    """Системная папка (или внутри неё), корень диска или сама папка профиля —
    такое Кеша не удаляет и не перезаписывает."""
    p = Path(path).expanduser().resolve()
    if p == Path(p.anchor):
        return True
    if p == Path.home().resolve() or p == Path.home().resolve().parent:
        return True
    for root in _protected_roots():
        if p == root or root in p.parents:
            return True
    return False


def check_delete(path) -> "str | None":
    if is_protected_path(path):
        return f"{path} — системная папка, удалять нельзя"
    return None
