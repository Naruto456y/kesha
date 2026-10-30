"""
Клод для Кеши: задачи на компьютере, для которых у Кеши нет готовой команды
(«WhatsApp на передний план»). GigaChat отвечает «ACT: <задача>» — задача уходит
в фоновый `claude -p` (Haiku, effort low), Кеша сразу говорит «Сейчас сделаю»,
а когда Клод закончит — озвучивает итог.

Безопасность: без MCP (нечем слать сообщения), без записи файлов, удаление и
выключение запрещены и правилами Клода, и проверкой задачи здесь.

Учёба: если Клод вернул «PS: <команда>», фраза запоминается в
data/learned_commands.json и в следующий раз выполняется локально, без Клода.
"""

import json
import os
import re
import shutil
import subprocess
import threading

from config import DATA_DIR, ROBOT_HOSTS, ROBOT_SSH, ROBOT_URL
from nlu import normalize

MODEL = "claude-haiku-5-5"
TIMEOUT = 180                     # сек на всю задачу (робот по SSH — дольше)
LEARNED_FILE = DATA_DIR / "learned_commands.json"
WORK_DIR = DATA_DIR / "claude_work"   # пустая папка: без CLAUDE.md проекта и лишнего контекста
ENABLED = True

ALLOWED_TOOLS = ["PowerShell", "Bash", "Read", "Glob", "Grep"]
DISALLOWED_TOOLS = [
    "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Agent",
    *(f"{t}({c} *)" for t in ("PowerShell", "Bash") for c in (
        "Remove-Item", "rm", "del", "rd", "rmdir", "erase", "format", "Format-Volume",
        "Stop-Computer", "Restart-Computer", "shutdown", "git push", "reg delete",
        "Clear-RecycleBin", "Set-ExecutionPolicy")),
]

SYSTEM = (
    "Ты руки голосового помощника Кеша на Windows-ноутбуке пользователя. Выполни задачу "
    "на компьютере быстро, минимумом шагов (PowerShell). Ничего не удаляй, не выключай "
    "и не перезагружай компьютер, не отправляй сообщения, не меняй системные настройки "
    "безопасности. Если задача опасная или непонятная — ничего не делай и так и скажи. "
    "Ответ: одно короткое предложение по-русски без эмодзи и разметки, что сделал "
    "(его озвучат голосом). "
    "Если действие можно повторить одной безопасной командой PowerShell, последней "
    "строкой напиши: PS: <команда>\n"
    f"Робот: Yahboom Raspbot V2 на Raspberry Pi 5, ssh {ROBOT_SSH} (по ключу; если имя не "
    f"находится — по IP: {', '.join(ROBOT_HOSTS[1:])}), код в /home/pi "
    "(robot_web_final.py, класс Robot из myrobot), окружение ~/giga_env. Веб-API робота: "
    f"{ROBOT_URL} — POST /api/move с JSON cmd (forward, backward, left, right, rotate_left, "
    "rotate_right, stop) и speed 0–255; ещё /api/camera и /api/rgb. Подробности — в "
    r"C:\Users\Yusuf\.claude\projects-details.md. "
    "SSH запускай с -o BatchMode=yes -o ConnectTimeout=5. Движение — коротко "
    "(1–2 секунды) и обязательно остановка моторов в конце; файлы на Pi не меняй."
)

# опасное не доверяем даже Клоду — отказ ещё до запуска
_DANGER = re.compile(
    r"удал|сотр|стер|очист|формат|выключи (комп|ноут|пк)|перезагруз|отправ|напиши .*(сообщ|письм)|"
    r"пароль|реестр|antivir|антивир|defender|брандмауэр|firewall|купи|оплат|перевед", re.I)
_PS_DANGER = re.compile(
    r"remove-item|\brm\b|\bdel\b|\brd\b|rmdir|format|stop-computer|restart-computer|shutdown|"
    r"reg\s+delete|clear-recyclebin|set-executionpolicy|invoke-expression|\biex\b|"
    r"invoke-webrequest|\biwr\b|downloadstring|-encodedcommand", re.I)
_EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿️‍]")
_PS_LINE = re.compile(r"^\s*PS\s*:\s*(.+?)\s*$", re.I | re.M)

_lock = threading.Lock()
_busy = threading.Event()


# ---------- выученные команды ----------
def _load() -> dict:
    try:
        with open(LEARNED_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data: dict):
    LEARNED_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = f"{LEARNED_FILE}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, LEARNED_FILE)


def learn(phrase: str, ps: str, answer: str):
    if _PS_DANGER.search(ps):
        return
    with _lock:
        data = _load()
        data[normalize(phrase)] = {"ps": ps, "answer": answer}
        _save(data)


def learned(phrase: str):
    """Фраза, которую Клод уже выполнял -> {"ps", "answer"} или None."""
    if not ENABLED:
        return None
    item = _load().get(normalize(phrase))
    return item if item and not _PS_DANGER.search(item.get("ps", "")) else None


def run_learned(item: dict) -> str:
    _run_ps(item["ps"])
    return item.get("answer") or "Готово."


def _run_ps(command: str):
    subprocess.Popen(["powershell", "-NoProfile", "-Command", command],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


# ---------- Клод ----------
def is_dangerous(task: str) -> bool:
    return bool(_DANGER.search(task))


def build_cmd(task: str) -> list:
    exe = shutil.which("claude") or "claude"
    return [exe, "-p", task, "--model", MODEL, "--effort", "low",
            "--output-format", "json", "--no-session-persistence",
            "--strict-mcp-config", "--setting-sources", "project",
            "--append-system-prompt", SYSTEM,
            "--allowedTools", *ALLOWED_TOOLS, "--disallowedTools", *DISALLOWED_TOOLS]


def _run_claude(task: str) -> str:
    """-> текст ответа Клода. Подписка, а не API: ANTHROPIC_API_KEY не передаём."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    out = subprocess.run(build_cmd(task), cwd=WORK_DIR, env=env, capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT,
                         stdin=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        data = json.loads(out.stdout)
    except ValueError:
        raise RuntimeError((out.stderr or out.stdout or "нет ответа").strip()[:200])
    if data.get("is_error"):
        raise RuntimeError(str(data.get("result") or data.get("subtype"))[:200])
    return (data.get("result") or "").strip()


def parse(result: str) -> "tuple[str, str | None]":
    """Ответ Клода -> (что сказать, PS-команда или None)."""
    m = _PS_LINE.search(result)
    ps = m.group(1).strip("` ") if m else None
    said = _PS_LINE.sub("", result).replace("`", "").replace("*", "")
    said = _EMOJI.sub("", said).strip()          # Silero эмодзи не читает
    return said or "Готово.", ps


def run(task: str, phrase: str, done) -> bool:
    """Запустить задачу в фоне. done(text) вызовется с итогом. False — уже занят."""
    if _busy.is_set():
        return False
    _busy.set()

    def work():
        try:
            said, ps = parse(_run_claude(task))
            if ps:
                learn(phrase, ps, said)
        except subprocess.TimeoutExpired:
            said = "Клод не успел, слишком долго."
        except Exception as e:
            print(f"[claude] {e}")
            said = "Клод не справился."
        finally:
            _busy.clear()
        done(said)

    threading.Thread(target=work, daemon=True, name="claude").start()
    return True
