"""
Список дел и заметки через TickTick: Кеша зовёт `claude -p` с облачным коннектором
claude.ai TickTick, Клод читает/создаёт задачи, а итог озвучивает Кеша.

    «список дел», «что мне сделать»        -> невыполненные задачи
    «добавь задачу помыть посуду»          -> новая задача (Входящие)
    «запиши заметку: купить молоко»        -> задача в проекте «Заметки»
    «мои заметки»                          -> задачи проекта «Заметки»
    «выполнил задачу молоко»               -> задача завершена

Отдельных команд тут нет: обработчики в features/notes.py сначала зовут try_add /
try_list / try_done; если TickTick выключен (ENABLED = False) или фраза не подошла —
они возвращают None и работают локальные заметки.
Удалять задачи Клоду запрещено.
"""

import json
import os
import re
import shutil
import subprocess
import threading

from config import DATA_DIR
from core import announce, short_answer, current_source
from features.notes import _NOTE_ADD, _TODO_ADD, _kind_of

MODEL = "claude-haiku-5-5"
TIMEOUT = 120
ENABLED = True
WORK_DIR = DATA_DIR / "claude_work"
NOTES_PROJECT = "Заметки"
CONNECTOR = "mcp__claude_ai_TickTick"

DISALLOWED_TOOLS = [f"{CONNECTOR}__delete_task", f"{CONNECTOR}__delete_tag",
                    f"{CONNECTOR}__delete_project_group", f"{CONNECTOR}__complete_tasks_in_project",
                    "Bash", "PowerShell", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Agent"]

SYSTEM = (
    "Ты помощник голосового ассистента Кеша. Работай ТОЛЬКО через инструменты TickTick. "
    "Задачи («дела») лежат в обычных проектах и во Входящих; заметки — задачи в проекте "
    f"«{NOTES_PROJECT}» (если проекта нет, создай его). Ничего не удаляй. Время и даты "
    "считай по Москве. Ответ озвучат голосом: максимум два коротких предложения по-русски, "
    "без эмодзи, markdown и списков с маркерами. Список перечисли через запятую, не больше "
    "7 пунктов, остальное — «и ещё N». Если пусто — так и скажи."
)

_LIST = ["мои заметки", "покажи заметки", "прочитай заметки", "какие заметки", "что в заметках",
         "список дел", "что в списке дел", "мои дела", "мои задачи", "какие задачи",
         "какие у меня дела", "что мне сделать", "что нужно сделать", "задачи на сегодня",
         "дела на сегодня", "что на сегодня", "что у меня в тикток", "что в тик ток"]
_DONE = ["выполнил задачу", "выполнила задачу", "сделал задачу", "сделала задачу",
         "задача выполнена", "отметь задачу", "вычеркни задачу", "вычеркни", "готово задача"]
_ADD_VERB = r"\b(?:запиши|добавь|сделай|создай|запомни|новая|новую)\b"

LIST_CACHE_SEC = 300        # повторное «список дел» за 5 минут отвечаем сразу, без Клода
_list_cache = {}            # задание Клоду -> (ответ, когда получен)
_busy = threading.Event()
_EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿️‍]")


def _build_cmd(task: str) -> list:
    exe = shutil.which("claude") or "claude"
    return [exe, "-p", task, "--model", MODEL, "--effort", "low",
            "--output-format", "json", "--no-session-persistence",
            "--setting-sources", "project", "--append-system-prompt", SYSTEM,
            "--allowedTools", CONNECTOR, "--disallowedTools", *DISALLOWED_TOOLS]


def _run_claude(task: str) -> str:
    """-> текст ответа Клода. Подписка, а не API: ANTHROPIC_API_KEY не передаём."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    out = subprocess.run(_build_cmd(task), cwd=WORK_DIR, env=env, capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT,
                         stdin=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        data = json.loads(out.stdout)
    except ValueError:
        raise RuntimeError((out.stderr or out.stdout or "нет ответа").strip()[:200])
    if data.get("is_error"):
        raise RuntimeError(str(data.get("result") or data.get("subtype"))[:200])
    return (data.get("result") or "").strip()


def _clean(text: str) -> str:
    text = _EMOJI.sub("", text.replace("`", "").replace("*", "").replace("#", ""))
    return re.sub(r"\s+", " ", text).strip() or "Готово."


def _ask(task: str, wait: str, cache: bool = False) -> str:
    """Запустить Клода в фоне; итог придёт через announce. -> что сказать сейчас.
    cache=True — чтение списка: свежий ответ отдаём сразу; любая запись кэш сбрасывает."""
    import time
    if cache:
        hit = _list_cache.get(task)
        if hit and time.time() - hit[1] < LIST_CACHE_SEC:
            return hit[0]
    else:
        _list_cache.clear()
    if _busy.is_set():
        return "TickTick ещё занят прошлой просьбой."
    _busy.set()
    source = current_source()

    def work():
        try:
            said = _clean(_run_claude(task))
            if cache:
                _list_cache[task] = (short_answer(said, 30), time.time())
        except subprocess.TimeoutExpired:
            said = "TickTick не ответил вовремя."
        except Exception as e:
            print(f"[ticktick] {e}")
            said = "Не получилось связаться с TickTick."
        finally:
            _busy.clear()
        announce(short_answer(said, 30), title="TickTick", speak=source == "voice")

    threading.Thread(target=work, daemon=True, name="ticktick").start()
    return wait


def try_add(text):
    if not ENABLED:
        return None
    from features.notes import _strip
    body = _strip(text, _TODO_ADD + _NOTE_ADD)
    if not body:
        return None                    # пусть спросит локальная команда: «Что записать?»
    if _kind_of(text) == "todo":
        task = f"Добавь во Входящие TickTick задачу: «{body}». Если названа дата или время — поставь срок."
    else:
        task = f"Добавь в проект «{NOTES_PROJECT}» TickTick заметку (задачу) с названием: «{body}»."
    return _ask(task, "Записываю в TickTick.")


def try_list(text):
    if not ENABLED or re.search(_ADD_VERB, text):
        return None
    if "замет" in text:
        task = f"Прочитай заметки: невыполненные задачи проекта «{NOTES_PROJECT}» в TickTick."
    elif "сегодня" in text:
        task = "Прочитай мои невыполненные задачи в TickTick на сегодня и просроченные."
    else:
        task = ("Прочитай мои невыполненные задачи в TickTick: сначала просроченные и на сегодня, "
                f"потом остальные ближайшие. Задачи проекта «{NOTES_PROJECT}» пропусти.")
    return _ask(task, "Смотрю TickTick.", cache=True)


def try_done(text):
    if not ENABLED:
        return None
    from features.notes import _strip
    body = _strip(text, ["задачу", "задача", "выполнил", "выполнила", "сделал", "сделала",
                         "выполнена", "отметь", "вычеркни", "готово"])
    if not body:
        return None
    return _ask(f"Найди в TickTick невыполненную задачу по описанию «{body}» и отметь её "
                "выполненной. Если подходящих несколько или нет ни одной — ничего не меняй, "
                "а скажи об этом.", "Отмечаю в TickTick.")
