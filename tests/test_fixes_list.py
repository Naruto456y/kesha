"""Список «Что исправить в Кеше» (29.10): питание, «я ухожу», ИИ, Алиса, почта, Озон,
несколько команд за раз, первая ссылка, музыка, разные формулировки. Всё на заглушках conftest."""
import pytest

import commands  # noqa: F401
import core
import session
from wake_text import addressed_to_other


def first(text):
    m = next(core._matching(text), None)
    return m and m["name"]


@pytest.mark.parametrize("text, name", [
    ("где мой телефон", "find_phone"), ("найди телефон", "find_phone"),
    ("я ухожу", "leaving_home"), ("мне пора", "leaving_home"),
    ("спящий режим", "sleep_pc"), ("гибернация", "hibernate_pc"), ("выключи экран", "monitor_off"),
    ("выйди из системы", "logoff_pc"), ("открой почту", "open_mail"), ("проверь почту", "open_mail"),
    ("найди на озоне наушники", "ozon"), ("добавь в корзину на озоне чехол", "ozon"),
    ("открой первую ссылку котики", "open_first_link"),
    ("найди рецепт борща и открой первую ссылку", "open_first_link"),
    ("спроси почему небо голубое", "ask_ai"), ("убери музыку", "music_pause"),
])
def test_new_commands(text, name):
    assert first(text) == name


@pytest.mark.parametrize("text, name", [
    ("можешь включить свет пожалуйста", "light_on"), ("врубишь музон", "play_music"),
    ("сделаешь погромчей", "volume_up"), ("найдешь котиков в интернете", "search_web"),
    ("глянь погоду", "get_weather_cmd"), ("открываешь ютуб", "open_youtube"),
    ("давай следующую песню", "music_next"), ("а можешь сказать который час", "get_time"),
    ("сколько щас градусов", "get_weather_cmd"), ("заблокируй комп пожалуйста", "lock_pc"),
])
def test_more_phrasings(monkeypatch, text, name):
    ran = []
    for c in core.registry.commands:
        monkeypatch.setitem(c, "func", lambda t, n=c["name"]: ran.append(n) or "ок")
    clean = core.fix_mixed_script(core.remove_wake_words(text))
    hit = core._exact(clean) or core._understand(clean, "test", session.get("test"))
    assert hit and hit[0]["name"] == name


@pytest.mark.parametrize("text, parts", [
    ("включи музыку и сделай громче", ["включи музыку", "сделай громче"]),
    ("открой почту и включи музыку", ["открой почту", "включи музыку"]),
    ("громче, потом пауза", ["громче", "пауза"]),
    ("включи свет и музыку", ["включи свет и музыку"]),
    ("запиши купить хлеб и молоко", ["запиши купить хлеб и молоко"]),
    ("найди рецепт борща и открой первую ссылку", ["найди рецепт борща и открой первую ссылку"]),
])
def test_split_commands(text, parts):
    assert core.split_commands(text) == parts


def test_multi_command_runs_both(monkeypatch):
    ran = []
    for c in core.registry.commands:
        monkeypatch.setitem(c, "func", lambda t, n=c["name"]: ran.append(n) or n)
    core.handle_command("включи музыку и сделай громче", ai=False)
    assert ran == ["play_music", "volume_up"]


def test_ai_answers_are_short():
    long = "Один два три четыре пять шесть семь восемь девять десять одиннадцать двенадцать"
    assert len(core.short_answer(long).split()) == 10
    assert core.short_answer("Париж. Это столица Франции и крупнейший город страны.") == "Париж. Это столица Франции и крупнейший город страны."
    assert core.short_answer("Небо голубое из-за рассеяния света. Короткие волны рассеиваются в воздухе намного сильнее длинных.") \
        == "Небо голубое из-за рассеяния света."


def test_ai_fix_only_returns_commands(monkeypatch):
    monkeypatch.setattr(core, "AI_AVAILABLE", True)
    monkeypatch.setattr(core, "_gig", object())
    for c in core.registry.commands:
        monkeypatch.setitem(c, "func", lambda t, n=c["name"]: n)
    monkeypatch.setattr(core, "ai_ask", lambda text, context="": "CMD: включи музыку")
    assert core.handle_command("вкл муззыку", ai=False) == "play_music"
    monkeypatch.setattr(core, "ai_ask", lambda text, context="": "Это просто разговор, а не команда.")
    assert core.handle_command("ну и дела", ai=False) == ""         # свободный ответ без «Кеша» не озвучиваем


@pytest.mark.parametrize("text, other", [
    ("Алиса, включи музыку", True), ("ну алиса громче", True), ("эй Маруся", True),
    ("Кеша включи свет", False), ("включи алису", False),
])
def test_other_assistant_ignored(text, other):
    assert addressed_to_other(text) is other
