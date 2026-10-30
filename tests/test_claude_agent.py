"""Клод для Кеши: ACT от GigaChat -> фоновый claude -p, опасное не пускаем, выученные команды."""
import threading

import pytest

import core
from core import handle_command
from features import claude_agent


@pytest.fixture
def act(monkeypatch):
    """GigaChat отвечает «ACT: …», Клод — заданным текстом; ждём фоновый поток."""
    said, tasks, finished = [], [], threading.Event()
    monkeypatch.setattr(core, "ai_ask", lambda text, context="": "ACT: выведи окно WhatsApp на передний план")
    monkeypatch.setattr(core, "announce", lambda text, title="", speak=True: said.append((text, speak)) or finished.set())

    def answer(reply):
        monkeypatch.setattr(claude_agent, "_run_claude", lambda task: tasks.append(task) or reply)
    return answer, said, tasks, finished


def test_act_goes_to_claude_and_result_is_spoken(act):
    answer, said, tasks, finished = act
    answer("Вывел WhatsApp на передний план.")
    assert handle_command("кеша ватсап на передний план", "voice") == "Сейчас сделаю."
    assert finished.wait(5)
    assert tasks == ["выведи окно WhatsApp на передний план"]
    assert said == [("Вывел WhatsApp на передний план.", True)]


def test_claude_learns_and_next_time_runs_locally(act, monkeypatch):
    answer, said, tasks, finished = act
    answer("Готово.\nPS: (New-Object -ComObject WScript.Shell).AppActivate('WhatsApp')")
    handle_command("кеша ватсап на передний план", "voice")
    assert finished.wait(5)
    ran = []
    monkeypatch.setattr(claude_agent, "_run_ps", lambda cmd: ran.append(cmd))
    monkeypatch.setattr(core, "ai_ask", lambda *a, **k: pytest.fail("второй раз без GigaChat"))
    assert handle_command("кеша ватсап на передний план", "voice") == "Готово."
    assert ran == ["(New-Object -ComObject WScript.Shell).AppActivate('WhatsApp')"] and len(tasks) == 1


def test_dangerous_ps_is_not_learned():
    claude_agent.learn("почисти загрузки", "Remove-Item $HOME\\Downloads\\* -Recurse", "Готово.")
    assert claude_agent.learned("почисти загрузки") is None


@pytest.mark.parametrize("task", ["удали папку загрузки", "отправь сообщение маме", "сотри все файлы на рабочем столе"])
def test_dangerous_task_never_reaches_claude(monkeypatch, task):
    monkeypatch.setattr(core, "ai_ask", lambda *a, **k: f"ACT: {task}")
    assert handle_command("кеша " + task, "voice") == "Такое не доверю даже Клоду."


def test_cmd_and_questions_do_not_go_to_claude(monkeypatch):
    monkeypatch.setattr(core, "ai_ask", lambda *a, **k: "Париж.")
    assert handle_command("кеша какая столица франции", "voice") == "Париж."


def test_without_wake_word_act_is_ignored(monkeypatch):
    monkeypatch.setattr(core, "ai_ask", lambda *a, **k: "ACT: выведи окно WhatsApp")
    assert not handle_command("ватсап на передний план", "voice", ai=False)


def test_busy_claude(monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(core, "ai_ask", lambda *a, **k: "ACT: сделай окно хрома поменьше")
    monkeypatch.setattr(core, "announce", lambda *a, **k: None)
    monkeypatch.setattr(claude_agent, "_run_claude", lambda task: gate.wait(5) and "ок")
    assert handle_command("кеша сделай окно хрома поменьше", "voice") == "Сейчас сделаю."
    assert handle_command("кеша сделай окно хрома поменьше", "voice") == "Клод ещё занят прошлой задачей."
    gate.set()


def test_cli_is_safe():
    cmd = claude_agent.build_cmd("x")
    assert cmd[cmd.index("--model") + 1] == "claude-haiku-5-5"
    assert cmd[cmd.index("--effort") + 1] == "low" and "--strict-mcp-config" in cmd
    deny = cmd[cmd.index("--disallowedTools") + 1:]
    assert "Write" in deny and "PowerShell(Remove-Item *)" in deny and "Bash(rm *)" in deny


def test_parse_strips_ps_line():
    assert claude_agent.parse("🗂️ Сделал.\nPS: `Start-Process taskmgr`") == ("Сделал.", "Start-Process taskmgr")


@pytest.mark.parametrize("phrase", ["робот помигай подсветкой", "пусть робот найдёт моё лицо"])
def test_robot_goes_straight_to_claude(act, monkeypatch, phrase):
    answer, said, tasks, finished = act
    monkeypatch.setattr(core, "ai_ask", lambda *a, **k: pytest.fail("GigaChat для робота не нужен"))
    answer("Робот проехал и остановился.")
    assert handle_command("кеша " + phrase, "voice") == "Сейчас сделаю."
    assert finished.wait(5) and tasks == ["робот Raspbot: " + phrase]


def test_robot_hint_in_system_prompt():
    assert "Raspbot" in claude_agent.SYSTEM and "projects-details.md" in claude_agent.SYSTEM
