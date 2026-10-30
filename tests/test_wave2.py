"""Тесты волны 2: синонимы, fuzzy, контекст, кэш GigaChat, лог."""
import json

import pytest

import ai_cache
import core
import nlu
import session
from core import CommandRegistry, handle_command


def _log(tmp_path):
    return (tmp_path / "kesha.log").read_text(encoding="utf-8")


# ---------- nlu ----------
def test_normalize():
    assert nlu.normalize("  Кеша, Включи СВЕТ!! Ёлка ") == "кеша включи свет елка"
    assert nlu.normalize("по-английски") == "по-английски"


def test_synonyms():
    n = nlu.normalize
    assert nlu.apply_synonyms(n("вруби лампу")) == "включи лампу"
    assert nlu.apply_synonyms(n("выруби комп")) == "выключи компьютер"
    assert nlu.apply_synonyms(n("прибавь звук")) == "прибавь громкость"
    assert nlu.apply_synonyms(n("врубить")) == "включи"
    # части слов не трогаем
    assert nlu.apply_synonyms(n("выключись")) == "выключись"


def _cmds():
    reg = CommandRegistry()

    @reg.command(["включи свет", "включи лампу"], "свет")
    def light_on(t): return "свет"

    @reg.command(["выключи свет"], "свет")
    def light_off(t): return "темно"

    @reg.command(["выключи компьютер"], "пк", risky=True)
    def shutdown(t): return "выкл"

    return reg


def test_fuzzy_catches_typos_and_rewrites():
    reg = _cmds()
    hit = nlu.fuzzy_find("включи лапму", reg.commands)
    assert hit.cmd["name"] == "light_on"
    assert hit.rewritten == "включи лампу"
    hit = nlu.fuzzy_find("ну вклчи свет", reg.commands)
    assert hit.rewritten == "ну включи свет"


def test_fuzzy_ignores_risky_unrelated_and_long_text():
    reg = _cmds()
    assert nlu.fuzzy_find("выключи компьтер", reg.commands) is None
    assert nlu.fuzzy_find("расскажи анекдот", reg.commands) is None
    assert nlu.fuzzy_find("я вчера думал включи лапму в общем и целом не знаю", reg.commands) is None


def test_fuzzy_requires_every_word_to_be_similar():
    """Живой случай: «сделай так чтобы...» совпало с «сделай фотку» на 0.82 и сделало селфи."""
    import commands  # noqa: F401
    assert nlu.fuzzy_find("сделай так чтобы в комнате стало светлее", core.registry.commands) is None
    reg = CommandRegistry()
    reg.command(["сделай фотку"])(lambda t: "фото")
    assert nlu.fuzzy_find("сделай так", reg.commands) is None
    assert nlu.fuzzy_find("сделай фотко", reg.commands) is not None


def test_macro_commands_are_exact_only():
    import commands  # noqa: F401
    risky = {c["name"] for c in core.registry.commands if c["risky"]}
    assert {"take_selfie", "call", "toggle_bluetooth", "type_text", "press_key"} <= risky


def test_fuzzy_ambiguous_returns_none():
    reg = CommandRegistry()
    reg.command(["включи музыку"])(lambda t: "a")
    reg.command(["включи музыка"])(lambda t: "b")
    assert nlu.fuzzy_find("включи музыкй", reg.commands) is None


# ---------- паттерны реальных команд ----------
# Эти команды отдают None, если фраза не их (open_app — «запусти музыку»,
# stop_alarm — «стоп», когда будильник не звонит), и пропускают дальше.
PASS_THROUGH = {"open_app", "stop_alarm", "translate_free"}   # делегируют другим командам


def test_real_patterns_do_not_shadow_each_other():
    import commands  # noqa: F401
    for c in core.registry.commands:
        for p in c["patterns"]:
            first = next(m for m in core._matching(p)
                         if m["name"] not in PASS_THROUGH or m["name"] == c["name"])
            assert first["name"] == c["name"], (p, c["name"], first["name"])


@pytest.mark.parametrize("phrase,name", [
    ("вруби лампу", "light_on"),
    ("включи лапму", "light_on"),
    ("потушы свет", "light_off"),
    ("поставь тайме на 5 минут", "set_timer"),
    ("пожалуйста вруби свет", "light_on"),
])
def test_real_registry_understands(phrase, name):
    import commands  # noqa: F401
    syn = nlu.apply_synonyms(nlu.normalize(phrase))
    hit = next(core._matching(syn, allow_risky=False), None)
    if hit is None:
        hit = nlu.fuzzy_find(syn, core.registry.commands).cmd
    assert hit["name"] == name


def test_dangerous_commands_are_risky():
    import commands  # noqa: F401
    risky = {c["name"] for c in core.registry.commands if c["risky"]}
    assert {"shutdown_pc", "restart_pc", "sleep_pc", "leaving_home", "start_chaos",
            "close_window", "close_app"} <= risky


def test_weather_city_parsing(monkeypatch):
    import commands
    assert commands._extract_city("какая погода в москве сегодня") == "москве"
    assert commands._extract_city("погода в нижнем новгороде") == "нижнем новгороде"
    assert commands._extract_city("погода") == commands.WEATHER_CITY
    assert commands._city_candidates("питере") == ["Санкт-Петербург"]
    assert "Москва" in [c.title() for c in commands._city_candidates("москве")]
    assert "казань" in commands._city_candidates("казани")

    class Resp:
        def __init__(self, code, data=None): self.status_code, self._d = code, data
        def json(self): return self._d

    asked = []

    def fake_get(url, params, timeout):
        asked.append(params["q"])
        if params["q"].lower() != "казань":
            return Resp(404)
        return Resp(200, {"name": "Казань", "main": {"temp": 11.6, "feels_like": 9.2, "humidity": 81},
                          "weather": [{"description": "дождь"}], "wind": {"speed": 3.4}})

    monkeypatch.setattr(commands.requests, "get", fake_get)
    assert commands.get_weather_cmd("погода в казани") == "Казань: 12°C, дождь, ветер 3 м/с"
    assert commands.get_weather_cmd("погода в казани подробно") == \
        "Казань: 12°C, дождь. Ощущается как 9°C, влажность 81%, ветер 3 м/с"
    assert commands.get_weather_cmd("погода в атлантиде") == "Не нашёл город атлантиде"


# ---------- handle_command с подменённым реестром ----------
class FakeGiga:
    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def chat(self, prompt):
        self.prompts.append(prompt)
        return self.replies.pop(0)


@pytest.fixture
def env(monkeypatch):
    reg = CommandRegistry()
    calls = []

    @reg.command(["включи свет", "включи лампу"], "Включить свет")
    def light_on(t):
        calls.append(("on", t)); return "свет включён"

    @reg.command(["погода"], "Погода", followup="погода в {arg}")
    def weather(t):
        calls.append(("weather", t)); return "погода: " + t

    @reg.command(["выключи компьютер"], "Выключить ПК", risky=True)
    def shutdown(t):
        calls.append(("shutdown", t)); return "выключаю"

    monkeypatch.setattr(core, "registry", reg)
    return calls


def test_synonym_stage(env):
    assert handle_command("Кеша, вруби лампу", "t") == "свет включён"
    assert env == [("on", "включи лампу")]


def test_fuzzy_stage_and_log(env, tmp_path):
    assert handle_command("включи лапму", "t") == "свет включён"
    assert "FUZZY | t | включи лапму" in _log(tmp_path)


def test_risky_only_by_exact_phrase(env, monkeypatch):
    monkeypatch.setattr(core, "ai_ask", lambda t: "CMD: выключи компьютер")
    assert handle_command("выруби комп", "t") != "выключаю"       # синоним не стреляет
    assert handle_command("выключи компьтер", "t") != "выключаю"  # fuzzy не стреляет
    assert not any(c[0] == "shutdown" for c in env)               # и GigaChat тоже
    assert handle_command("выключи компьютер", "t") == "выключаю"


def test_negation_and_questions_skip_smart_stages(env, monkeypatch):
    monkeypatch.setattr(core, "ai_ask", lambda t: "ответ")
    assert handle_command("не вруби свет", "t") == "ответ"
    assert handle_command("объясни как вруби свет", "t") == "ответ"
    assert env == []


def test_followup_context(env, tmp_path):
    assert handle_command("погода в москве", "t") == "погода: погода в москве"
    assert handle_command("а в питере?", "t") == "погода: погода в питере"
    assert "FOLLOWUP | t | а в питере?" in _log(tmp_path)


def test_followup_expires_and_is_per_source(env, monkeypatch):
    handle_command("погода", "voice")
    monkeypatch.setattr(core, "ai_ask", lambda t: "ответ")
    assert handle_command("а в питере", "telegram") == "ответ"       # другой источник
    monkeypatch.setattr(session, "SESSION_TTL", -1)
    assert handle_command("а в питере", "voice") == "ответ"          # протухло


def test_ai_rewrites_into_command(env, monkeypatch, tmp_path):
    giga = FakeGiga(["CMD: включи свет"])
    monkeypatch.setattr(core, "_gig", giga)
    monkeypatch.setattr(core, "AI_AVAILABLE", True)
    assert handle_command("сделай посветлее в комнате", "t") == "свет включён"
    assert "- включи свет / включи лампу" in giga.prompts[0]
    assert "выключи компьютер" not in giga.prompts[0]     # опасные не отправляем
    assert "AI_CMD | t" in _log(tmp_path)


@pytest.mark.parametrize("reply", ["Включи свет", "Включить свет | включи свет", "включи лампу."])
def test_ai_reply_without_cmd_prefix(env, monkeypatch, reply):
    """GigaChat забыл «CMD:» и ответил фразой команды — всё равно выполняем."""
    monkeypatch.setattr(core, "ai_ask", lambda t: reply)
    assert handle_command("сделай посветлее", "t") == "свет включён"


def test_ai_normal_answer_is_not_a_command(env, monkeypatch):
    monkeypatch.setattr(core, "ai_ask", lambda t: "Включи свет в комнате, если темно — так полезнее для глаз.")
    assert handle_command("почему болят глаза", "t").startswith("Включи свет в комнате")
    assert env == []


def test_ai_bad_command_is_not_executed(env, monkeypatch, tmp_path):
    monkeypatch.setattr(core, "_gig", FakeGiga(["CMD: выключи компьютер"]))
    monkeypatch.setattr(core, "AI_AVAILABLE", True)
    assert handle_command("мне пора спать, выруби всё", "t") == "Не понял команду."
    assert env == []
    assert "UNKNOWN" in _log(tmp_path)


def test_ai_cache_saves_tokens(env, monkeypatch):
    giga = FakeGiga(["Париж", "не должно быть вызвано"])
    monkeypatch.setattr(core, "_gig", giga)
    monkeypatch.setattr(core, "AI_AVAILABLE", True)
    assert handle_command("Столица Франции?", "t") == "Париж"
    assert handle_command("столица франции", "voice") == "Париж"
    assert len(giga.prompts) == 1


def test_ai_gets_context_only_for_followups(env, monkeypatch):
    giga = FakeGiga(["Париж", "Около двух миллионов", "Лондон"])
    monkeypatch.setattr(core, "_gig", giga)
    monkeypatch.setattr(core, "AI_AVAILABLE", True)
    handle_command("столица франции", "t")
    assert "Предыдущий диалог" not in giga.prompts[0]
    handle_command("а сколько там жителей", "t")
    assert "Кеша: Париж" in giga.prompts[1]
    handle_command("столица англии", "t")
    assert "Предыдущий диалог" not in giga.prompts[2]


def test_unknown_phrase_logged(env, monkeypatch, tmp_path):
    monkeypatch.setattr(core, "AI_AVAILABLE", False)
    assert handle_command("бла бла бла", "voice") == "Не понял команду."
    assert "UNKNOWN | voice | бла бла бла" in _log(tmp_path)


# ---------- кэш и сессия ----------
def test_ai_cache_ttl_persist_and_limit(tmp_path):
    path = tmp_path / "c.json"
    c = ai_cache.AICache(path, ttl=100, max_items=2)
    c.put("a", "1"); c.put("b", "2"); c.put("c", "3")
    assert c.get("a") is None and c.get("c") == "3"
    assert ai_cache.AICache(path, ttl=100, max_items=2).get("c") == "3"   # переживает перезапуск
    data = json.loads(path.read_text(encoding="utf-8"))
    data["c"]["ts"] -= 1000
    path.write_text(json.dumps(data), encoding="utf-8")
    assert ai_cache.AICache(path, ttl=100).get("c") is None


def test_session_keeps_last_steps_only():
    s = session.Session()
    for i in range(5):
        s.remember(f"q{i}", f"a{i}")
    assert [e["text"] for e in s.recent()] == ["q2", "q3", "q4"]


def test_followup_regex_does_not_grab_normal_questions():
    s = session.Session()
    s.remember("погода", "ок", "погода в {arg}")
    assert s.resolve_followup("а в питере") == "погода в питере"
    assert s.resolve_followup("а ты кто") is None
    assert s.resolve_followup("а в чем смысл жизни вообще") is None
