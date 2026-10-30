collect_ignore = ["manual"]  # ручные проверки моделей/микрофона, pytest их не трогает

import pytest

import ai_cache
import klog
import notify
import session
import settings


class _FakePopen:
    """Вместо настоящего процесса: тесты не запускают программы (Telegram, Яндекс Музыку...)."""
    returncode = 0
    pid = 0
    stdout = stderr = stdin = None

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def communicate(self, *a, **k):
        return b"", b""

    def poll(self):
        return 0

    def wait(self, *a, **k):
        return 0

    def kill(self):
        pass

    terminate = kill


@pytest.fixture(autouse=True)
def no_real_side_effects(monkeypatch):
    """Никаких программ, сайтов, нажатий и сворачивания окон из тестов.
    Тест, которому нужен вызов, сам подменяет функцию поверх этой заглушки."""
    import os
    import subprocess
    import webbrowser
    noop = lambda *a, **k: None   # noqa: E731
    monkeypatch.setattr(os, "startfile", noop, raising=False)
    monkeypatch.setattr(os, "system", lambda *a, **k: 0)
    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    for n in ("open", "open_new", "open_new_tab"):
        monkeypatch.setattr(webbrowser, n, noop)
    try:
        import keyboard
        import mouse
        for n in ("send", "write", "press", "release", "press_and_release"):
            monkeypatch.setattr(keyboard, n, noop)
        for n in ("move", "click", "double_click", "right_click", "wheel", "press", "release"):
            monkeypatch.setattr(mouse, n, noop)
    except Exception:
        pass
    try:
        import AppOpener
        monkeypatch.setattr(AppOpener, "open", noop)
        monkeypatch.setattr(AppOpener, "close", noop)
    except Exception:
        pass
    try:
        from voice import duck
        monkeypatch.setattr(duck, "_sessions", lambda: [])     # микшер Windows не трогаем
    except Exception:
        pass
    try:
        import ctypes
        user32 = ctypes.windll.user32
        for n in ("ShowWindow", "keybd_event", "mouse_event", "SendInput"):
            monkeypatch.setattr(user32, n, lambda *a, **k: 0)
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch, no_real_side_effects):
    """Тесты не трогают реальные logs/, data/ и не показывают всплывашки."""
    klog.set_path(tmp_path / "kesha.log")
    monkeypatch.setattr(ai_cache.cache, "path", tmp_path / "ai_cache.json")
    monkeypatch.setattr(ai_cache.cache, "_data", None)
    settings.use_file(tmp_path / "settings.json")
    monkeypatch.setattr(notify, "enabled", False)
    session.reset()

    try:
        import commands  # noqa: F401  — тот же порядок регистрации, что в main.py
        from features import reminders, notes, stats, agenda, messenger
    except Exception:
        yield
        return
    monkeypatch.setattr(reminders, "store", reminders.ReminderStore(tmp_path / "reminders.json"))
    monkeypatch.setattr(notes, "store", notes.NotesStore(tmp_path / "notes.json"))
    stats.use_db(tmp_path / "stats.db")
    agenda.use_file(tmp_path / "calendar.json")
    monkeypatch.setattr(agenda, "ics_urls", [])
    monkeypatch.setattr(messenger, "users_file", tmp_path / "telegram_users.json")
    monkeypatch.setattr(messenger, "contacts", {})
    import app_index
    monkeypatch.setattr(app_index, "shortcuts", lambda refresh=False: {})   # не реальные ярлыки ПК
    monkeypatch.setattr(commands, "_set_volume", lambda level: True)        # громкость ПК не трогаем
    from features import utilities
    monkeypatch.setattr(utilities, "set_mute", lambda on: True)
    from features import claude_agent                                         # Клода по-настоящему не зовём
    monkeypatch.setattr(claude_agent, "LEARNED_FILE", tmp_path / "learned_commands.json")
    monkeypatch.setattr(claude_agent, "_run_claude", lambda task: pytest.fail("реальный claude -p в тесте"))
    monkeypatch.setattr(claude_agent, "_run_ps", lambda cmd: None)
    from features import robot                                                # робот не ездит
    monkeypatch.setattr(robot, "_post", lambda host, cmd, speed: None)
    monkeypatch.setattr(robot, "_stop_later", lambda sec: None)
    monkeypatch.setattr(robot, "_last", 0.0)                                  # окно «назад» без «робот» закрыто
    yield
    stats.use_db(tmp_path / "stats_closed.db")
