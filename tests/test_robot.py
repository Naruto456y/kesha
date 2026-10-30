"""Робот Raspbot: движения напрямую через /api/move, остальное — Клоду."""
import pytest

import core
from core import handle_command
from features import robot


@pytest.fixture
def moves(monkeypatch):
    sent, stops = [], []
    monkeypatch.setattr(robot, "move", lambda cmd, speed=0: sent.append(cmd))
    monkeypatch.setattr(robot, "_stop_later", lambda sec: stops.append(sec))
    return sent, stops


@pytest.mark.parametrize("phrase,cmd,said", [
    ("робот вперёд", "forward", "Еду вперёд."),
    ("пусть робот поедет назад", "backward", "Еду назад."),
    ("скажи роботу чтобы поехал вперёд", "forward", "Еду вперёд."),
    ("робот налево", "left", "Еду влево."),
    ("робот развернись", "rotate_left", "Разворачиваюсь."),
    ("робот стоп", "stop", "Стою."),
    ("робот едь в правый бок", "right", "Еду вправо."),
    ("робот впеерёд", "forward", "Еду вперёд."),
])
def test_robot_moves(moves, phrase, cmd, said):
    sent, stops = moves
    assert handle_command(phrase, "voice") == said
    assert sent == [cmd] and (stops == [] if cmd == "stop" else len(stops) == 1)


@pytest.mark.parametrize("phrase,sec", [("робот вперёд", 1.0), ("робот вперёд на 3 секунды", 3),
                                        ("робот назад две секунды", 2), ("робот вперёд 60 секунд", 5),
                                        ("робот вперёд на полсекунды", 0.5), ("назад полторы секунды", 1.5)])
def test_robot_seconds(phrase, sec):
    assert robot.seconds(phrase) == sec


def test_robot_voice_command_untouched(moves):
    sent, _ = moves
    assert "робот" in handle_command("голос робота", "voice").lower() and sent == []


def test_robot_offline(monkeypatch):
    def fail(cmd, speed=0):
        raise ConnectionError("нет сети")
    monkeypatch.setattr(robot, "move", fail)
    assert handle_command("робот вперёд", "voice").startswith("Робот не отвечает.")


def test_other_robot_things_go_to_claude(moves, monkeypatch):
    asked = []
    monkeypatch.setattr(core, "_ask_claude", lambda task, clean, source: asked.append(task) or (None, "Сейчас сделаю."))
    assert handle_command("кеша робот помигай подсветкой", "voice") == "Сейчас сделаю."
    assert asked == ["робот Raspbot: робот помигай подсветкой"] and moves[0] == []


def test_robot_falls_back_to_next_host(monkeypatch):
    import requests
    tried = []

    def post(host, cmd, speed):
        tried.append(host)
        if host == "yahboom":
            raise requests.ConnectionError("имя не найдено")
    monkeypatch.setattr(robot, "_post", post)
    monkeypatch.setattr(robot, "_host", "yahboom")
    robot.move("stop")
    robot.move("stop")
    assert tried == ["yahboom", "192.168.10.112", "192.168.10.112"]   # второй раз — сразу рабочий


def test_followup_without_word_robot(moves, monkeypatch):
    sent, stops = moves
    monkeypatch.setattr(robot, "_last", 0.0)
    assert handle_command("назад", "voice", ai=False) != "Еду назад." and sent == []   # робота не звали
    handle_command("робот вперёд", "voice")
    assert handle_command("назад на 2 секунды", "voice", ai=False) == "Еду назад."
    assert sent == ["forward", "backward"] and stops[-1] == 2
    monkeypatch.setattr(robot, "_last", robot.time.time() - robot.FOLLOWUP_SEC - 1)
    handle_command("назад", "voice", ai=False)
    assert sent == ["forward", "backward"]                                             # окно прошло


def test_gigachat_token_refresh():
    calls = []

    class Gig:
        _token = "old"

        def chat(self, prompt):
            calls.append(self._token)
            if self._token == "old":
                raise Exception('GigaChat API error 401: {"message":"Token has expired"}')
            return "ок"
    g = Gig()
    g_chat = core.gig_chat
    # токен сброшен -> help_manager сам возьмёт новый; тут имитируем это
    orig = Gig.chat
    Gig.chat = lambda self, p: orig(self, p) if self._token else (setattr(self, "_token", "new") or orig(self, p))
    assert g_chat(g, "привет") == "ок" and calls == ["old", "new"]
