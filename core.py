"""
Ядро проекта Кеша.
Реестр команд + handle_command + шина событий + AI fallback.

Конвейер распознавания handle_command (волна 2):
  1. точное совпадение паттерна
  2. синонимы        («вруби лампу»  -> «включи лампу»)
  3. follow-up       («а в Питере?»  -> «погода в питере»)
  4. нечёткий поиск  (опечатки, искажения распознавания)
  5. GigaChat        (перефразировать в команду ИЛИ ответить на вопрос)
Шаги 2–5 никогда не запускают опасные команды (risky=True) —
их можно вызвать только точной фразой.
"""

from dotenv import load_dotenv
load_dotenv()  # загружаем .env из корня проекта

import re

import klog
import session
from ai_cache import cache as ai_cache
from config import WAKE_WORDS, AI_COMMANDS_MAX_WORDS
from nlu import normalize, apply_synonyms, fuzzy_find, is_question, has_negation


# ============================================================
#  РЕЕСТР КОМАНД
# ============================================================
class CommandRegistry:
    """Хранит все команды проекта.
    Каждая команда регистрируется через декоратор @registry.command(...)"""

    def __init__(self):
        self.commands = []

    def command(self, patterns, description="", category="Общее", priority=0,
                risky=False, followup=None):
        """risky   — опасная команда: только точная фраза, без fuzzy/синонимов/GigaChat.
        followup — шаблон уточнения для «а в Питере?», например "погода в {arg}"."""
        def decorator(func):
            self.commands.append({
                "patterns": [p.lower() for p in patterns],
                "func": func,
                "description": description,
                "category": category,
                "priority": priority,
                "risky": risky,
                "followup": followup,
                "name": func.__name__,
            })
            self.commands.sort(key=lambda c: -c.get("priority", 0))
            return func
        return decorator

    def get_all(self):
        return list(self.commands)


# Глобальный реестр — единственный на весь проект
registry = CommandRegistry()


# ============================================================
#  ШИНА СОБЫТИЙ
# ============================================================
_subscribers = []


def subscribe(callback):
    """Подписаться на события ядра.
    callback(source: str, text: str, response: str)"""
    if callback not in _subscribers:
        _subscribers.append(callback)


def unsubscribe(callback):
    if callback in _subscribers:
        _subscribers.remove(callback)


def emit_event(source: str, text: str, response: str):
    """Разослать событие всем подписчикам."""
    for cb in list(_subscribers):
        try:
            cb(source, text, response)
        except Exception as e:
            print(f"[emit_event] Ошибка в подписчике {cb}: {e}")


# ============================================================
#  AI HELPER (GigaChat)
# ============================================================
try:
    from help_manager import GigaChat
    _gig = GigaChat()
    AI_AVAILABLE = True
except Exception as e:
    print(f"[core] GigaChat недоступен: {e}")
    _gig = None
    AI_AVAILABLE = False

_CMD_REPLY = re.compile(r"^\s*CMD\s*:\s*(.+?)\s*$", re.I | re.S)


def _commands_hint() -> str:
    """Список безопасных команд для GigaChat: «описание: фраза | фраза | фраза»."""
    lines = []
    for c in registry.commands:
        if c.get("risky"):
            continue
        lines.append(f"- {c['description']}: " + " | ".join(c["patterns"][:3]))
    return "\n".join(lines)


def _build_prompt(text: str, context: str, with_commands: bool) -> str:
    parts = ["Ты голосовой помощник Кеша. Отвечай кратко и по делу. Без смайликов."]
    if with_commands:
        parts.append(
            "Если фраза пользователя — это одна из команд ниже, сказанная другими словами "
            "(перефразирование, сленг, опечатка), ответь ТОЛЬКО одной строкой: "
            "CMD: <команда из списка, с параметрами пользователя: запрос, город, число>. "
            "Если это вопрос или разговор, а не команда — просто ответь на него, без CMD.\n"
            "Команды:\n" + _commands_hint()
        )
    if context:
        parts.append("Предыдущий диалог:\n" + context)
    parts.append("Фраза пользователя: " + text)
    return "\n\n".join(parts)


def ai_ask(text: str, context: str = "") -> str:
    """Спросить GigaChat. Ответ вида «CMD: <команда>» значит, что фраза — команда
    (разбирает handle_command). Одинаковые вопросы берём из кэша (без контекста)."""
    if not AI_AVAILABLE or _gig is None:
        return "Не понял команду."
    key = "" if context else normalize(text)
    cached = ai_cache.get(key)
    if cached is not None:
        return cached
    try:
        with_commands = len(text.split()) <= AI_COMMANDS_MAX_WORDS
        answer = _gig.chat(_build_prompt(text, context, with_commands))
        answer = (answer or "").strip()
        if not answer:
            return "Не понял команду."
        if not _CMD_REPLY.match(answer):
            for ch in '*%»`#$"':
                answer = answer.replace(ch, "")
            answer = answer.strip()
        ai_cache.put(key, answer)
        return answer
    except Exception as e:
        print(f"[ai_ask] {e}")
        return "Не понял команду."


# ============================================================
#  ХЕЛПЕРЫ
# ============================================================
def remove_wake_words(text: str) -> str:
    text = text.lower().strip()
    for word in WAKE_WORDS:
        text = text.replace(word, "")
    return text.strip()


def _matching(text: str, allow_risky: bool = True):
    """Команды, чей паттерн встречается в тексте, по убыванию приоритета."""
    for cmd in registry.commands:
        if cmd.get("risky") and not allow_risky:
            continue
        if any(re.search(r'\b' + re.escape(p) + r'\b', text) for p in cmd["patterns"]):
            yield cmd


def _exact(text: str, allow_risky: bool = True):
    """Выполнить первую подошедшую команду. -> (cmd, ответ) или None.
    Команда может вернуть None — «не моё», тогда пробуем следующую."""
    for cmd in _matching(text, allow_risky):
        try:
            response = cmd["func"](text)
        except Exception as e:
            print(f"[{cmd['name']}] Ошибка: {e}")
            continue
        if response is not None:
            return cmd, response
    return None


def _understand(clean: str, source: str, sess):
    """Шаги 2–4: синонимы, follow-up, fuzzy. -> (cmd, ответ) или None."""
    norm = normalize(clean)
    if not norm or has_negation(norm):
        return None

    # follow-up: «а в питере»
    followup = sess.resolve_followup(norm)
    if followup:
        hit = _exact(followup, allow_risky=False)
        if hit:
            klog.phrase("FOLLOWUP", source, clean, f"{followup} -> {hit[0]['name']}")
            return hit

    if is_question(norm):
        return None

    # синонимы: «вруби лампу»
    syn = apply_synonyms(norm)
    if syn != norm:
        hit = _exact(syn, allow_risky=False)
        if hit:
            klog.phrase("SYNONYM", source, clean, f"{syn} -> {hit[0]['name']}")
            return hit

    # fuzzy: «включи лапму»
    m = fuzzy_find(syn, registry.commands)
    if m:
        hit = _exact(m.rewritten, allow_risky=False)
        if hit:
            klog.phrase("FUZZY", source, clean,
                        f"{m.pattern!r} {m.score:.2f} -> {hit[0]['name']}")
            return hit
    return None


def _ask_ai(clean: str, source: str, sess):
    """Шаг 5. -> (cmd или None, ответ)."""
    norm = normalize(clean)
    ctx = sess.context() if session.looks_like_followup(norm) else ""
    answer = ai_ask(clean, context=ctx) if ctx else ai_ask(clean)

    m = _CMD_REPLY.match(answer)
    if not m:
        klog.phrase("UNKNOWN", source, clean, "ответ: " + answer[:80])
        return None, answer

    rewritten = m.group(1).strip(" \"'«»`.").lower()
    hit = _exact(rewritten, allow_risky=False)
    if hit:
        klog.phrase("AI_CMD", source, clean, f"{rewritten!r} -> {hit[0]['name']}")
        return hit
    klog.phrase("UNKNOWN", source, clean, f"AI предложил {rewritten!r}, но команды нет")
    return None, "Не понял команду."


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
def handle_command(text: str, source: str = "app") -> str:
    """
    Принимает команду от любого интерфейса.
    :param source: "app" | "telegram" | "alice" | "website" | "voice"
    """
    if not text or not text.strip():
        return ""

    clean = remove_wake_words(text)
    sess = session.get(source)

    hit = _exact(clean) or _understand(clean, source, sess)
    cmd, response = hit if hit else _ask_ai(clean, source, sess)

    sess.remember(clean, response, cmd.get("followup") if cmd else None)
    emit_event(source, text, response)
    return response


# ============================================================
#  УТИЛИТЫ
# ============================================================
def list_commands():
    """Вывести все зарегистрированные команды."""
    if not registry.commands:
        print("[core] Реестр пуст. Подключи commands.py в main.py.")
        return
    print(f"\n[core] Зарегистрировано команд: {len(registry.commands)}")
    print("=" * 60)
    for cmd in registry.commands:
        patterns = ", ".join(cmd["patterns"])
        print(f"  [{cmd['category']:12}] {cmd['name']:20} ← {patterns}")
    print("=" * 60)


if __name__ == "__main__":
    print("Проверка core.py")
    print("AI доступен:", AI_AVAILABLE)

    def test_sub(source, text, response):
        print(f"  [event] {source}: '{text}' -> '{response}'")

    subscribe(test_sub)

    print("\nТест handle_command:")
    result = handle_command("привет", source="app")
    print(f"  Ответ: {result}")
