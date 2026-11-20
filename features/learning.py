"""
Обучение Кеши голосом и память о хозяине.

    «когда я говорю вкладочка, это значит вкладка»  -> правило исправления (corrector.py)
    «забудь исправление вкладочка»
    «чему ты научилась», «какие исправления»

    «запомни, что я люблю пиццу»        -> факт в память
    «что ты обо мне знаешь»             -> факты
    «забудь про пиццу»                  -> убрать факт
    «что я люблю?»                      -> отвечает GigaChat, факты подставляются в запрос

Память — обычная заметка Obsidian «Память Кеши.md» (её можно править руками);
если хранилища нет — data/memory.md.
"""
import re
import threading

import corrector
from config import DATA_DIR
from core import registry

# ---------- исправления ----------
_TEACH = re.compile(
    r"когда\s+(?:я\s+)?(?:говорю|скажу|сказал|слышишь)\s+(.+?)[\s,]+"
    r"(?:это значит|я имею в виду|имею в виду|значит|это|делай|выполняй)\s+(.+)$")


@registry.command(["когда я говорю", "когда я скажу", "когда я сказал", "когда слышишь", "когда говорю"],
                  "Научить Кешу понимать слово или фразу", "Обучение", priority=15)
def teach_correction(text):
    m = _TEACH.search(" ".join(text.replace(",", " ").split()))
    if not m:
        return "Скажи так: когда я говорю икс, это значит игрек."
    wrong, right = m.group(1).strip(" .«»\"'"), m.group(2).strip(" .«»\"'")
    if not corrector.teach(wrong, right):
        return "Это одно и то же, запоминать нечего."
    return f"Запомнил: «{wrong}» значит «{right}»."


@registry.command(["забудь исправление", "забудь правило", "удали исправление", "удали правило"],
                  "Забыть исправление", "Обучение", priority=15)
def forget_correction(text):
    body = re.sub(r"\b(?:забудь|удали)\s+(?:исправление|правило)\b", " ", text).strip(" .:«»\"'")
    if not body:
        return "Какое исправление забыть?"
    return f"Забыл про «{body}»." if corrector.forget(body) else f"Правила про «{body}» у меня нет."


@registry.command(["чему ты научилась", "чему ты научился", "какие исправления", "мои исправления",
                   "что ты выучила", "что ты выучил", "покажи исправления"],
                  "Показать выученные исправления", "Обучение", priority=12)
def list_corrections(text):
    r = corrector.rules()
    pairs = list(r["words"].items()) + list(r["phrases"].items())
    if not pairs:
        return "Пока ничему: исправления появляются, когда ты повторяешь непонятую фразу."
    shown = ", ".join(f"«{w}» это «{g}»" for w, g in pairs[-5:])
    return f"Выучил исправлений: {len(pairs)}. Последние: {shown}."


# ---------- память ----------
MEMORY_NOTE = "30 Я/Память Кеши.md"
MEMORY_MAX = 40
_HEADER = "# Память Кеши\n\nЧто Кеша знает обо мне. Строки можно править и удалять руками.\n\n"
_ABOUT_ME = re.compile(r"\b(?:я|мой|моя|мое|моё|мои|моего|моей|моих|меня|мне|мной|у нас|наш|наша)\b")
_lock = threading.Lock()
memory_path = None      # тесты подменяют; None — выбрать по хранилищу


def _path():
    if memory_path is not None:
        return memory_path
    from features import obsidian
    return obsidian.VAULT / MEMORY_NOTE if obsidian.available() else DATA_DIR / "memory.md"


def facts() -> list:
    try:
        lines = _path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [ln[2:].strip() for ln in lines if ln.startswith("- ") and ln[2:].strip()]


def _write(items):
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_HEADER + "".join(f"- {i}\n" for i in items), encoding="utf-8")
    try:
        import ai_cache
        ai_cache.cache.clear()      # старые ответы GigaChat могли опираться на старые факты
    except Exception:
        pass


def facts_for_prompt() -> str:
    return "\n".join(f"- {f}" for f in facts()[-MEMORY_MAX:])


@registry.command(["запомни что", "запомни, что", "запомни про меня", "запомни обо мне"],
                  "Запомнить факт о хозяине", "Память", priority=13)
def remember_fact(text):
    body = re.sub(r"^.*?запомни(?:,)?\s+(?:что|про меня|обо мне)\b[\s,:]*", "", text).strip(" .")
    if not body:
        return "Что запомнить?"
    if not _ABOUT_ME.search(body) and "про меня" not in text and "обо мне" not in text:
        return None                 # «запомни что купить молоко» — это заметка, не факт обо мне
    with _lock:
        items = facts()
        if body.lower() in (i.lower() for i in items):
            return "Это я уже помню."
        _write(items + [body])
    return "Запомнил."


@registry.command(["что ты обо мне знаешь", "что ты знаешь обо мне", "что ты про меня знаешь",
                   "что ты помнишь обо мне", "что ты помнишь", "что ты запомнила", "что ты запомнил"],
                  "Рассказать, что Кеша помнит", "Память", priority=13)
def recall_facts(text):
    items = facts()
    if not items:
        return "Пока ничего. Скажи: запомни, что я люблю пиццу."
    more = f" И ещё {len(items) - 6}." if len(items) > 6 else ""
    return "Я помню: " + "; ".join(items[-6:]) + "." + more


@registry.command(["забудь что", "забудь, что", "забудь про"], "Забыть факт", "Память", priority=13)
def forget_fact(text):
    body = re.sub(r"^.*?забудь(?:,)?\s+(?:что|про)\b[\s,:]*", "", text).strip(" .")
    stems = [w[:max(4, len(w) - 2)] for w in re.findall(r"[a-zа-яё0-9]+", body.lower())
             if len(w) > 3 and not _ABOUT_ME.fullmatch(w)]
    if not stems:
        return "Что именно забыть?"
    with _lock:
        items = facts()
        keep = [i for i in items if not all(s in i.lower() for s in stems)]
        if len(keep) == len(items):
            return "Такого я и не помню."
        _write(keep)
    return "Забыл."
