"""Слово «Кеша» в тексте, fuzzy-поиск и детектор openWakeWord."""
import numpy as np
import pytest

from wake_text import has_wake, strip_wake, from_last_wake
from nlu import fix_mixed_script, fuzzy_find, normalize
from core import registry, remove_wake_words, handle_command


@pytest.mark.parametrize("text, cmd", [
    ("Кеша, открой браузер", "открой браузер"),           # большая буква и запятая (Aqua)
    ("открой браузер, кеша", "открой браузер"),
    ("открой, Кеша, браузер", "открой, браузер"),
    ("ну кеша включи музыку", "включи музыку"),
    ("Эй, Кеша! Который час?", "Который час?"),
    ("каша который час", "который час"),                    # алиас в начале
    ("кеща включи свет", "включи свет"),                    # на 1 букву от «кеша» в начале
    ("Кешу позови", "позови"),
])
def test_wake_found_and_stripped(text, cmd):
    assert has_wake(text) and strip_wake(text) == cmd


@pytest.mark.parametrize("text", [
    "очисти кэш браузера", "покажи кешбэк", "кешью купи", "на завтрак была каша",
    "Лёша привет", "кушать хочу",
])
def test_no_false_wake(text):
    assert not has_wake(text) and strip_wake(text) == text


def test_remove_wake_words_keeps_other_words():
    assert remove_wake_words("Кеша, очисти кэш браузера") == "очисти кэш браузера"
    assert remove_wake_words("напечатай привет!!!") == "напечатай привет!!!"


def test_from_last_wake_ignores_aliases():
    assert from_last_wake("бла бла каша тут кеша включи свет") == "кеша включи свет"
    assert from_last_wake("каша на завтрак") == ""


def test_mixed_script_goes_to_majority():
    assert fix_mixed_script("youтube") == "youtube"
    assert fix_mixed_script("включи музыкy") == "включи музыку"


def test_single_word_fuzzy_only_at_start():
    import commands  # noqa: F401 — регистрирует команды
    assert fuzzy_find(normalize("очисти кэш браузера"), registry.commands) is None
    hit = fuzzy_find(normalize("ну погромчи"), registry.commands)
    assert hit and hit.pattern == "погромче"


def test_question_with_typo_still_matches(monkeypatch):
    import core
    ran = []
    monkeypatch.setattr(core, "_exact", lambda text, allow_risky=True: ran.append(text) or ({"name": "x"}, "ок"))
    import session
    assert core._understand("какая пагода", "test", session.get("test"))
    assert ran == ["какая погода"]                     # паттерн начинается с того же «какая»
    ran.clear()
    assert core._understand("где я", "test", session.get("test")) is None and ran == []


def test_oww_feed_runs_on_untrained_head(tmp_path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("openwakeword")
    from voice import oww_wake
    if not all((oww_wake.OWW_DIR / f"{n}.onnx").exists() for n in oww_wake.FEATURE_MODELS):
        pytest.skip("нет моделей признаков openWakeWord")
    path = tmp_path / "head.pt"
    torch.save({"state": oww_wake.build_head().state_dict(), "threshold": 2.0}, path)   # порог 2 — не сработает
    det = oww_wake.OwwWakeDetector(head_path=path)
    hits = 0
    for _ in range(30):
        hits, fired = det.feed(np.zeros(oww_wake.CHUNK, dtype=np.int16), hits)
        assert not fired


@pytest.mark.parametrize("text, name", [
    ("громче", "volume_up"), ("ну тише", "volume_down"), ("пауза", "music_pause"),
    ("дальше", "music_next"), ("скролл вниз", "scroll_down"), ("левый клик", "click_left"),
    ("давай дальше смотреть это видео", None), ("стоп это не то", None),
])
def test_quick_control_without_wake(monkeypatch, text, name):
    import commands  # noqa: F401
    import core
    for c in core.registry.commands:
        if c["name"] in core.QUICK_CONTROL:
            monkeypatch.setitem(c, "func", lambda t, n=c["name"]: n)
    hit = core.quick_control(text)
    assert (hit[0] if hit else None) == name


class _Vol:
    def __init__(self, v): self.v = v
    def GetMasterVolume(self): return self.v
    def SetMasterVolume(self, v, ctx): self.v = v


class _Sess:
    def __init__(self, pid, v): self.ProcessId, self.SimpleAudioVolume = pid, _Vol(v)


def test_duck_lowers_other_apps_and_restores(monkeypatch):
    from voice import duck
    music, quiet = _Sess(10, 0.9), _Sess(11, 0.1)
    monkeypatch.setattr(duck, "_sessions", lambda: [music, quiet])
    duck.duck(0.2)
    duck.duck(0.2)                                   # второй раз «до» не перезаписывает
    assert music.SimpleAudioVolume.v == 0.2 and quiet.SimpleAudioVolume.v == 0.1
    duck.restore()
    assert music.SimpleAudioVolume.v == 0.9 and quiet.SimpleAudioVolume.v == 0.1
    assert not duck.is_ducked()
