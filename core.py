"""
Ядро проекта Кеша.
Реестр команд + handle_command + шина событий + AI fallback.
"""

from dotenv import load_dotenv
load_dotenv()  # загружаем .env из корня проекта

import re

from config import WAKE_WORDS


# ============================================================
#  РЕЕСТР КОМАНД
# ============================================================
class CommandRegistry:
    """Хранит все команды проекта.
    Каждая команда регистрируется через декоратор @registry.command(...)"""

    def __init__(self):
        self.commands = []

    def command(self, patterns, description="", category="Общее", priority=0):
        def decorator(func):
            self.commands.append({
                "patterns": [p.lower() for p in patterns],
                "func": func,
                "description": description,
                "category": category,
                "priority": priority,
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


def ai_ask(text: str) -> str:
    if not AI_AVAILABLE or _gig is None:
        return "Не понял команду."
    try:
        answer = _gig.chat(
            "Отвечай кратко и по делу как голосовой помощник. "
            "Без смайликов. Вопрос: " + text
        )
        for ch in '*%»`#$"':
            answer = answer.replace(ch, "")
        return answer.strip() if answer else "Не понял команду."
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

    for cmd in registry.commands:
        if any(re.search(r'\b' + re.escape(p) + r'\b', clean) for p in cmd["patterns"]):
            try:
                response = cmd["func"](clean)
                if response is not None:
                    emit_event(source, text, response)
                    return response
            except Exception as e:
                print(f"[{cmd['name']}] Ошибка: {e}")
                continue

    response = ai_ask(clean)
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