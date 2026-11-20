"""Исправление слов (corrector), обучение голосом и память, Obsidian, база голоса, кэш TickTick."""
import time

import numpy as np
import pytest

import corrector
import core
from core import handle_command
from features import learning, obsidian, ticktick
from voice import voicedb


# ---------- corrector ----------
def test_no_rules_text_untouched():
    assert corrector.apply("Включи Лампу") == "Включи Лампу"


def test_pair_becomes_rule_after_two_times():
    assert corrector.note_fix("новая вкладочка", "новая вкладка") is False
    assert corrector.apply("новая вкладочка") == "новая вкладочка"
    assert corrector.note_fix("новая вкладочка", "новая вкладка") is True
    assert corrector.apply("новая вкладочка") == "новая вкладка"
    assert corrector.apply("открой новая вкладочка сейчас") == "открой новая вкладка сейчас"   # выучено слово


def test_real_command_word_is_not_a_mistake():
    """«включи свет» -> «выключи свет»: оба слова настоящие, это другая команда, а не ошибка."""
    for _ in range(3):
        corrector.note_fix("включи музыку", "выключи музыку")
    assert corrector.apply("включи музыку") == "включи музыку"


def test_unrelated_phrases_not_learned():
    for _ in range(3):
        corrector.note_fix("расскажи анекдот", "какая погода")
    assert corrector.apply("расскажи анекдот") == "расскажи анекдот"


def test_repeat_after_failure_is_learned():
    for _ in range(2):
        corrector.note_failure("voice", "включи лапму")
        corrector.note_success("voice", "включи лампу")
    assert corrector.apply("ну включи лапму") == "ну включи лампу"


def test_late_repeat_ignored(monkeypatch):
    for _ in range(2):
        corrector.note_failure("voice", "включи лапму")
        corrector._pending["voice"] = ("включи лапму", time.time() - 100)
        corrector.note_success("voice", "включи лампу")
    assert corrector.apply("включи лапму") == "включи лапму"


def test_rules_survive_restart(tmp_path):
    corrector.teach("псидион", "обсидиан")
    corrector.use_file(tmp_path / "corrections.json")       # «перезапуск»: заново с диска
    assert corrector.apply("открой псидион") == "открой обсидиан"


def test_learned_fix_runs_command_without_ai(monkeypatch):
    monkeypatch.setattr(core, "ai_ask", lambda *a, **k: pytest.fail("GigaChat не нужен"))
    corrector.teach("сколька врмени", "сколько времени")
    assert handle_command("сколька врмени", source="voice")


# ---------- обучение голосом ----------
def test_teach_by_voice():
    reply = handle_command("когда я говорю вкладочка это значит вкладка")
    assert "вкладочка" in reply and "вкладка" in reply
    assert corrector.apply("новая вкладочка") == "новая вкладка"
    assert "1" in handle_command("чему ты научился")
    assert "Забыл" in handle_command("забудь исправление вкладочка")
    assert corrector.apply("новая вкладочка") == "новая вкладочка"


# ---------- память ----------
def test_memory_remember_recall_forget():
    assert handle_command("запомни что я люблю пиццу") == "Запомнил."
    assert handle_command("запомни что я люблю пиццу") == "Это я уже помню."
    assert "пиццу" in handle_command("что ты обо мне знаешь")
    assert "я люблю пиццу" in learning.facts_for_prompt()
    assert handle_command("забудь про пиццу") == "Забыл."
    assert learning.facts() == []


def test_memory_goes_into_ai_prompt():
    handle_command("запомни что мой любимый цвет синий")
    assert "мой любимый цвет синий" in core._build_prompt("какой мой любимый цвет", "", False)


def test_remember_not_about_me_is_a_note():
    """«запомни что купить молоко» — заметка, а не факт о хозяине."""
    handle_command("запомни что купить молоко")
    assert learning.facts() == []


# ---------- Obsidian ----------
@pytest.fixture
def vault(tmp_path):
    v = tmp_path / "vault"
    (v / "20 Цели").mkdir(parents=True)
    (v / "99 Система").mkdir()
    (v / "20 Цели" / "Бэклог идей.md").write_text("# Бэклог идей\n- старая идея\n", encoding="utf-8")
    (v / "20 Цели" / "Цели.md").write_text("# Цели\n- [ ] купить **ноутбук** для [[колледж|колледжа]]\n", encoding="utf-8")
    (v / "Робот.md").write_text("Raspbot едет вперёд. Робот, робот.", encoding="utf-8")
    (v / "99 Система" / "Шаблон.md").write_text("робот", encoding="utf-8")
    return v


def test_obsidian_missing_vault():
    assert "не найдено" in handle_command("запиши в обсидиан купить термопасту")


def test_obsidian_add_goes_to_inbox(vault):
    assert handle_command("запиши в обсидиан купить термопасту и вентилятор") == "Записал в Obsidian."
    text = (vault / obsidian.INBOX_NOTE).read_text(encoding="utf-8")
    assert "купить термопасту и вентилятор" in text and f"## {time.strftime('%Y-%m-%d')}" in text
    handle_command("запиши в дневник второе")
    assert (vault / obsidian.INBOX_NOTE).read_text(encoding="utf-8").count("## ") == 1   # дата одна на день


def test_obsidian_idea_appends_to_backlog(vault):
    assert handle_command("запиши идею сделать роботу глаза") == "Идею записал."
    text = (vault / "20 Цели" / "Бэклог идей.md").read_text(encoding="utf-8")
    assert "старая идея" in text and "сделать роботу глаза" in text


def test_obsidian_search_and_open(vault, monkeypatch):
    opened = []
    monkeypatch.setattr(obsidian.os, "startfile", opened.append, raising=False)
    reply = handle_command("найди в обсидиане про робота", source="voice")
    assert "Робот" in reply and "Шаблон" not in reply          # служебная папка не ищется
    assert "Открываю" in handle_command("да", source="voice")
    assert opened and opened[0].startswith("obsidian://open?path=") and "%D0%A0" in opened[0]


def test_obsidian_search_nothing(vault):
    assert "ничего нет" in handle_command("найди в заметках про динозавров")


def test_obsidian_open_with_typo(vault, monkeypatch):
    opened = []
    monkeypatch.setattr(obsidian.os, "startfile", opened.append, raising=False)
    assert "Бэклог идей" in handle_command("открой заметку беклог идеи")
    assert len(opened) == 1


def test_obsidian_read_strips_markdown(vault):
    reply = handle_command("прочитай заметку цели")
    assert "купить ноутбук для колледжа" in reply
    assert "[" not in reply and "*" not in reply


# ---------- база голоса ----------
def _tone(sec=1.0):
    t = np.arange(int(16000 * sec)) / 16000
    return (np.sin(2 * np.pi * 220 * t) * 8000).astype(np.int16)


def test_voicedb_saves_wav_and_row():
    assert voicedb.save("command", _tone().tobytes(), "открой браузер")
    assert voicedb.save("wake_pos", _tone(1.8), "кеша", score=0.97)
    voicedb.drain()
    rows = voicedb.rows()
    assert {r[1] for r in rows} == {"command", "wake_pos"}
    cmd = next(r for r in rows if r[1] == "command")
    assert cmd[3] == "открой браузер" and abs(cmd[4] - 1.0) < 0.01
    import wave
    with wave.open(cmd[2]) as w:
        assert w.getframerate() == 16000 and w.getnframes() == 16000
    assert voicedb.stats()["command"][0] == 1


def test_voicedb_respects_setting_and_garbage():
    import settings
    assert voicedb.save("command", b"abc", "обрезанный буфер") is False
    assert voicedb.save("command", _tone(0.1), "слишком коротко") is False
    assert voicedb.save("ambient", _tone(), "фон не пишем") is False
    settings.set("voice_db", False)
    assert voicedb.save("command", _tone(), "выключено") is False
    voicedb.drain()
    assert voicedb.rows() == []


def test_voicedb_negatives_limited(monkeypatch):
    monkeypatch.setattr(voicedb, "NEG_PER_HOUR", 3)
    monkeypatch.setattr(voicedb, "_neg_times", [])
    assert [voicedb.save("wake_neg", _tone(), "наташа") for _ in range(5)] == [True] * 3 + [False] * 2
    voicedb.drain()


def test_voicedb_prunes_oldest(monkeypatch):
    monkeypatch.setattr(voicedb, "MAX_MB", 0.1)          # ~3 секунды звука
    for i in range(6):
        voicedb.save("command", _tone(), f"фраза {i}")
        voicedb.drain()
    texts = [r[3] for r in voicedb.rows()]
    assert "фраза 5" in texts and "фраза 0" not in texts
    assert voicedb.stats()["mb"] <= 0.11


# ---------- кэш TickTick ----------
def test_ticktick_list_cached_until_write(monkeypatch):
    calls = []
    monkeypatch.setattr(ticktick, "ENABLED", True)
    monkeypatch.setattr(ticktick, "_list_cache", {})
    monkeypatch.setattr(ticktick, "_run_claude", lambda task: calls.append(task) or "Купить хлеб, сделать уроки.")
    monkeypatch.setattr(ticktick, "announce", lambda *a, **k: None)

    def wait():
        for _ in range(100):
            if not ticktick._busy.is_set():
                return
            time.sleep(0.01)

    assert ticktick.try_list("список дел") == "Смотрю TickTick."
    wait()
    assert ticktick.try_list("список дел") == "Купить хлеб, сделать уроки."     # сразу, без Клода
    assert len(calls) == 1
    ticktick.try_add("добавь задачу помыть посуду")
    wait()
    assert ticktick.try_list("список дел") == "Смотрю TickTick."                # после записи кэш сброшен
    wait()
