"""
Заметки и список дел (волна 4): data/notes.json.

    «Кеша, запиши: купить молоко»          -> заметка
    «добавь в список дел помыть посуду»    -> задача
    «мои заметки», «список дел»
    «выполнил задачу 2», «удали заметку 1», «очисти список дел»
"""

import json
import os
import re
import threading
import uuid
from datetime import datetime

from config import NOTES_FILE
from core import registry


class NotesStore:
    def __init__(self, path=NOTES_FILE):
        self.path = path
        self._lock = threading.RLock()
        self._items = None

    def _load(self):
        if self._items is not None:
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self._items = data.get("notes", []) if isinstance(data, dict) else []
        except (OSError, ValueError):
            self._items = []

    def _save(self):
        tmp = f"{self.path}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"notes": self._items}, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError as e:
            print(f"[notes] не удалось сохранить: {e}")

    def add(self, text, kind="note"):
        item = {"id": uuid.uuid4().hex[:8], "text": text, "kind": kind, "done": False,
                "created": datetime.now().isoformat(timespec="seconds")}
        with self._lock:
            self._load()
            self._items.append(item)
            self._save()
        return item

    def items(self, kind, include_done=False):
        with self._lock:
            self._load()
            return [i for i in self._items if i["kind"] == kind and (include_done or not i["done"])]

    def update(self, item_id, **fields):
        with self._lock:
            self._load()
            for i in self._items:
                if i["id"] == item_id:
                    i.update(fields)
                    self._save()
                    return i
        return None

    def remove(self, ids):
        ids = set(ids)
        with self._lock:
            self._load()
            before = len(self._items)
            self._items = [i for i in self._items if i["id"] not in ids]
            self._save()
            return before - len(self._items)


store = NotesStore()

_NOTE_ADD = ["сделай заметку", "создай заметку", "добавь заметку", "новая заметка",
             "запиши в заметки", "запиши заметку", "запиши в заметку", "запиши", "запомни",
             "заметка"]
_TODO_ADD = ["добавь в список дел", "добавь в дела", "добавь задачу", "новая задача",
             "в список дел", "добавь в туду", "добавь в todo", "запиши в дела",
             "запиши задачу", "создай задачу"]
_FILLER = {"что", "это", "пожалуйста", "мне", "-", "надо", "нужно"}


def _strip(text, words):
    t = text
    for w in sorted(words, key=len, reverse=True):
        t = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", " ", t)
    t = t.replace(":", " ")
    tokens = t.split()
    while tokens and tokens[0] in _FILLER:
        tokens.pop(0)
    return " ".join(tokens)


def _kind_of(text):
    return "todo" if re.search(r"\b(дел|дела|задач\w*|туду|todo)\b", text) else "note"


def _pick(items, text):
    """Номер («задачу 2») или кусок текста («задачу молоко»)."""
    m = re.search(r"\b(\d+)\b", text)
    if m:
        n = int(m.group(1))
        return items[n - 1] if 1 <= n <= len(items) else None
    words = [w for w in text.split() if len(w) > 3]
    for item in items:
        if any(w[:5] in item["text"].lower() for w in words):
            return item
    return None


@registry.command(_TODO_ADD, "Добавить задачу", "Заметки", priority=8)
def add_todo(text):
    body = _strip(text, _TODO_ADD)
    if not body:
        return "Какую задачу добавить?"
    store.add(body, "todo")
    return f"Добавил в список дел: {body}"


@registry.command(_NOTE_ADD, "Записать заметку", "Заметки", priority=6)
def add_note(text):
    body = _strip(text, _NOTE_ADD)
    if not body:
        return "Что записать?"
    store.add(body, "note")
    return f"Записал: {body}"


@registry.command(
    ["мои заметки", "покажи заметки", "прочитай заметки", "какие заметки", "что в заметках",
     "список дел", "что в списке дел", "мои дела", "мои задачи", "какие задачи",
     "какие у меня дела", "что мне сделать", "что нужно сделать",
     "где заметка", "где заметки", "где мои заметки", "покажи заметку"],
    "Прочитать заметки/дела", "Заметки", priority=7,
)
def list_notes(text):
    if re.search(r"\b(?:запиши|добавь|сделай|создай|запомни|новая)\b", text):
        return None            # «запиши в заметки ...» — это add_note
    kind = _kind_of(text) if "замет" not in text else "note"
    if "что мне сделать" in text or "что нужно сделать" in text:
        kind = "todo"
    items = store.items(kind)
    if not items:
        return "Список дел пуст." if kind == "todo" else "Заметок нет."
    head = "Дела" if kind == "todo" else "Заметки"
    return head + ":\n" + "\n".join(f"{n}. {i['text']}" for n, i in enumerate(items, 1))


@registry.command(
    ["выполнил задачу", "выполнила задачу", "сделал задачу", "сделала задачу",
     "задача выполнена", "отметь задачу", "вычеркни задачу", "вычеркни", "готово задача"],
    "Отметить задачу выполненной", "Заметки", priority=8,
)
def done_todo(text):
    items = store.items("todo")
    if not items:
        return "Список дел пуст."
    item = _pick(items, _strip(text, ["задачу", "задача", "выполнил", "выполнила",
                                      "сделал", "сделала", "выполнена", "отметь", "вычеркни"]))
    if item is None:
        return "Какую задачу? Скажи номер, например: «выполнил задачу 1»."
    store.update(item["id"], done=True)
    left = len(items) - 1
    return f"Отлично! «{item['text']}» выполнено. Осталось дел: {left}."


@registry.command(
    ["удали заметку", "удали задачу", "очисти заметки", "удали все заметки",
     "очисти список дел", "удали все задачи", "удали все дела"],
    "Удалить заметку/задачу", "Заметки", priority=8,
)
def delete_notes(text):
    kind = "todo" if re.search(r"\b(задач\w*|дел|дела)\b", text) else "note"
    items = store.items(kind, include_done=True)
    if not items:
        return "Список дел пуст." if kind == "todo" else "Заметок нет."
    if "очисти" in text or "все" in text.split():
        store.remove([i["id"] for i in items])
        return "Список дел очищен." if kind == "todo" else "Все заметки удалены."
    item = _pick(store.items(kind), _strip(text, ["удали", "заметку", "задачу"]))
    if item is None:
        return "Какую? Скажи номер, например: «удали заметку 1»."
    store.remove([item["id"]])
    return f"Удалил: {item['text']}"
