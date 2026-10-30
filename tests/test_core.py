import core
from core import CommandRegistry, handle_command, remove_wake_words, subscribe, unsubscribe


def test_remove_wake_words():
    assert remove_wake_words("Кеша, открой браузер") == "открой браузер"
    assert remove_wake_words("Кеша, запиши: молоко!") == "запиши: молоко!"
    assert remove_wake_words("открой браузер, кеша") == "открой браузер"


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


def test_every_registered_command_takes_one_text_argument():
    """Ловит ошибку, когда декоратор случайно оказался над хелпером."""
    import inspect
    import commands  # noqa: F401
    from core import registry
    for c in registry.commands:
        assert not c["name"].startswith("_"), c["name"]
        params = [p for p in inspect.signature(c["func"]).parameters.values()
                  if p.default is inspect.Parameter.empty]
        assert len(params) == 1, c["name"]
