"""
Obsidian: Кеша пишет и ищет прямо в хранилище (папка с .md), без Клода и интернета.

    «запиши в обсидиан купить термопасту»   -> строка во «Входящие.md» под сегодняшней датой
    «запиши идею сделать Кеше глаза»         -> строка в «Бэклог идей.md»
    «найди в обсидиане про робота»           -> в каких заметках есть, «Открыть первую?»
    «открой заметку цели»                    -> откроет в Obsidian
    «прочитай заметку список покупок»        -> зачитает начало

Хранилище: OBSIDIAN_VAULT в .env, иначе ../../notes (папка Python/notes).
"""
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from rapidfuzz import fuzz, process

from config import OBSIDIAN_VAULT
from core import registry, ask_yes_no

VAULT = Path(OBSIDIAN_VAULT)
INBOX_NOTE = "00 Главное/Входящие.md"
IDEAS_NOTE = "Бэклог идей"            # ищется по названию; нет — создаётся рядом со «Входящими»
SKIP_DIRS = {".obsidian", ".trash", ".git", "99 Система"}
READ_WORDS = 60
_STOP = {"про", "для", "что", "как", "это", "или", "все", "мои", "моя", "мой", "где", "там", "насчет"}
_lock = threading.Lock()


def available() -> bool:
    return VAULT.is_dir()


def notes() -> list:
    """Все заметки хранилища (Path), без служебных папок."""
    out = []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        out += [Path(root) / f for f in files if f.lower().endswith(".md")]
    return out


def _stems(query: str) -> list:
    words = [w for w in re.findall(r"[a-zа-яё0-9]+", query.lower().replace("ё", "е"))
             if len(w) >= 3 and w not in _STOP]
    return [w[:len(w) - 2] if len(w) > 5 else w for w in words]


def find_note(name: str):
    """Заметка по названию (с опечатками) или None."""
    items = {p.stem.lower().replace("ё", "е"): p for p in notes()}
    key = " ".join(name.lower().replace("ё", "е").split())
    if not key or not items:
        return None
    if key in items:
        return items[key]
    hit = process.extractOne(key, list(items), scorer=fuzz.WRatio, score_cutoff=78)
    return items[hit[0]] if hit else None


def search(query: str, limit: int = 5) -> list:
    """Заметки, где есть все слова запроса: сначала по названию, потом по числу упоминаний."""
    stems = _stems(query)
    if not stems:
        return []
    scored = []
    for p in notes():
        title = p.stem.lower().replace("ё", "е")
        in_title = sum(s in title for s in stems)
        try:
            body = p.read_text(encoding="utf-8", errors="ignore").lower().replace("ё", "е")
        except OSError:
            body = ""
        if not all(s in title or s in body for s in stems):
            continue
        scored.append((in_title, sum(body.count(s) for s in stems), p))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2].stem))
    return [p for _, _, p in scored[:limit]]


def open_note(p: Path):
    os.startfile("obsidian://open?path=" + quote(str(p), safe=""))


def append_line(note: Path, line: str, dated: bool = True):
    """Дописать строку в заметку; dated — под заголовком сегодняшней даты."""
    now = datetime.now()
    with _lock:
        note.parent.mkdir(parents=True, exist_ok=True)
        text = note.read_text(encoding="utf-8") if note.exists() else f"# {note.stem}\n"
        if not text.endswith("\n"):
            text += "\n"
        if dated:
            head = f"## {now:%Y-%m-%d}"
            if head not in text:
                text += f"\n{head}\n"
            text += f"- {now:%H:%M} {line}\n"
        else:
            text += f"- {line}\n"
        note.write_text(text, encoding="utf-8")


def _plain(md: str) -> str:
    """Markdown -> текст для озвучки."""
    md = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.S)             # frontmatter
    md = re.sub(r"```.*?```", " ", md, flags=re.S)
    md = re.sub(r"!\[\[.*?\]\]|!\[.*?\]\(.*?\)", " ", md)
    md = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", md)        # [[заметка|текст]] -> текст
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)
    md = re.sub(r"^\s*[-*+]\s+(\[.\]\s*)?", "", md, flags=re.M)
    md = re.sub(r"[#*_`>|]", " ", md)
    return " ".join(md.split())


_ADD = ["запиши в обсидиан", "запиши в обсидиане", "добавь в обсидиан", "заметка в обсидиан",
        "запиши в дневник", "добавь в дневник", "запиши мысль"]
_IDEA = ["запиши идею", "добавь идею", "новая идея", "идея для бэклога"]
_SEARCH = ["найди в обсидиане", "найди в обсидиан", "поищи в обсидиане", "поиск в обсидиане",
           "найди в заметках", "поищи в заметках", "что в обсидиане про", "что в обсидиане о",
           "что у меня записано про", "что у меня записано о", "что я писал про", "что я писал о",
           "найди заметку"]
_OPEN = ["открой заметку", "открой в обсидиане заметку", "открой в обсидиане"]
_READ = ["прочитай заметку", "зачитай заметку", "прочти заметку", "что в заметке"]


def _body(text, patterns):
    for p in sorted(patterns, key=len, reverse=True):
        m = re.search(r"\b" + re.escape(p) + r"\b", text)
        if m:
            return text[m.end():].strip(" :,.—-")
    return ""


def _off():
    return "Хранилище Obsidian не найдено. Укажи путь в OBSIDIAN_VAULT."


@registry.command(_ADD, "Записать в Obsidian", "Obsidian", priority=12)
def obsidian_add(text):
    if not available():
        return _off()
    body = _body(text, _ADD)
    if not body:
        return "Что записать в Obsidian?"
    append_line(VAULT / INBOX_NOTE, body)
    return "Записал в Obsidian."


@registry.command(_IDEA, "Записать идею в Obsidian", "Obsidian", priority=12)
def obsidian_idea(text):
    if not available():
        return None                     # без хранилища — обычная заметка
    body = _body(text, _IDEA)
    if not body:
        return "Какую идею записать?"
    note = find_note(IDEAS_NOTE) or (VAULT / INBOX_NOTE).with_name(IDEAS_NOTE + ".md")
    append_line(note, f"{body} ({datetime.now():%d.%m.%Y})", dated=False)
    return "Идею записал."


@registry.command(_SEARCH, "Поиск по заметкам Obsidian", "Obsidian", priority=12)
def obsidian_search(text):
    if not available():
        return _off()
    query = _body(text, _SEARCH)
    if not query:
        return "Что найти в заметках?"
    hits = search(query)
    if not hits:
        return f"В заметках про «{query}» ничего нет."
    names = ", ".join(p.stem for p in hits[:3])
    first = hits[0]

    def yes():
        open_note(first)
        return f"Открываю «{first.stem}»."
    ask_yes_no(yes)
    if len(hits) == 1:
        return f"Нашёл в заметке «{first.stem}». Открыть?"
    return f"Нашёл в заметках: {names}. Открыть первую?"


@registry.command(_OPEN, "Открыть заметку Obsidian", "Obsidian", priority=12)
def obsidian_open(text):
    if not available():
        return _off()
    name = _body(text, _OPEN)
    if not name:
        return "Какую заметку открыть?"
    note = find_note(name) or next(iter(search(name, 1)), None)
    if note is None:
        return f"Не нашёл заметку «{name}»."
    open_note(note)
    return f"Открываю «{note.stem}»."


@registry.command(_READ, "Прочитать заметку Obsidian", "Obsidian", priority=12)
def obsidian_read(text):
    if not available():
        return _off()
    name = _body(text, _READ)
    if not name:
        return "Какую заметку прочитать?"
    note = find_note(name) or next(iter(search(name, 1)), None)
    if note is None:
        return f"Не нашёл заметку «{name}»."
    words = _plain(note.read_text(encoding="utf-8", errors="ignore")).split()
    if not words:
        return f"Заметка «{note.stem}» пустая."
    tail = " И так далее." if len(words) > READ_WORDS else ""
    return f"{note.stem}. " + " ".join(words[:READ_WORDS]) + tail
