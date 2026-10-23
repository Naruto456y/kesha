import core
from core import CommandRegistry, handle_command, remove_wake_words, subscribe, unsubscribe


def test_remove_wake_words():
    assert remove_wake_words("Кеша, открой браузер") == ", открой браузер"


def test_registry_sorts_by_priority():
    reg = CommandRegistry()

    @reg.command(["а"], priority=0)
    def low(text):
        return "low"

    @reg.command(["б"], priority=5)
    def high(text):
        return "high"

    assert [c["name"] for c in reg.get_all()] == ["high", "low"]


def test_empty_input():
    assert handle_command("   ") == ""


def test_event_bus(monkeypatch):
    monkeypatch.setattr(core, "ai_ask", lambda t: "ответ")
    monkeypatch.setattr(core, "registry", CommandRegistry())
    seen = []
    cb = lambda s, t, r: seen.append((s, t, r))
    subscribe(cb)
    try:
        assert handle_command("что-то непонятное", source="test") == "ответ"
    finally:
        unsubscribe(cb)
    assert seen == [("test", "что-то непонятное", "ответ")]
