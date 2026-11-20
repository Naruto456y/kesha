"""«Нажми кнопку ОК»: поиск кнопки по названию. Реальные окна не трогаем."""
import commands
from features import click_button as cb


def test_clean_target():
    assert cb.clean_target("на кнопку ОК") == "ок"
    assert cb.clean_target("по кнопке «Сохранить»") == "сохранить"


def test_score_aliases_and_fuzzy():
    assert cb.score("ок", "OK") == 100
    assert cb.score("отмена", "Cancel") == 100
    assert cb.score("сохранить", "&Сохранить") == 100
    assert cb.score("сохранить", "Сохранить как") >= cb.MIN_SCORE
    assert cb.score("ок", "Блокнот") < cb.MIN_SCORE


def test_best_match_prefers_exact():
    els = [("Сохранить как", 1), ("Сохранить", 2), ("Отмена", 3)]
    assert cb.best_match("сохранить", els)[0] == 2
    assert cb.best_match("удалить", els) is None


def test_click_by_name_falls_back_to_ocr(monkeypatch):
    monkeypatch.setattr(cb, "click_uia", lambda t: None)
    monkeypatch.setattr(cb, "click_ocr", lambda t: "ok")
    assert cb.click_by_name("кнопку ок") == (True, "Нажал «ok»")
    monkeypatch.setattr(cb, "click_ocr", lambda t: None)
    assert cb.click_by_name("ок")[0] is False


def test_command_extracts_target(monkeypatch):
    seen = []
    monkeypatch.setattr(cb, "click_by_name", lambda t: (seen.append(t), (True, "ok"))[1])
    cb.click_button("кликни по кнопке Далее")
    assert seen == ["далее"]


def test_press_key_delegates_unknown_key(monkeypatch):
    seen = []
    monkeypatch.setattr(cb, "click_by_name", lambda t: (seen.append(t), (True, "Нажал «OK»"))[1])
    assert commands.press_key("нажми кнопку ок") == "Нажал «OK»"
    assert seen == ["ок"]


def test_press_key_real_key_not_delegated(monkeypatch):
    sent = []
    monkeypatch.setattr(commands.keyboard, "send", lambda k: sent.append(k))
    monkeypatch.setattr(cb, "click_by_name", lambda t: (_ for _ in ()).throw(AssertionError("не кнопка")))
    commands.press_key("нажми клавишу enter")
    assert sent == ["enter"]
