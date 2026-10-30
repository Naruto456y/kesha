"""
Робот Yahboom Raspbot V2: «робот вперёд / назад / влево / вправо / развернись / стоп».
Кеша шлёт POST /api/move на robot-web.service (robot_web_final.py на Pi) и через
ROBOT_MOVE_SEC останавливает моторы. Всё остальное про робота («робот, сфоткай»)
команда не берёт — уходит Клоду (core._ask_ai).
"""

import re
import threading
import time

import requests

from config import ROBOT_HOSTS, ROBOT_MOVE_SEC, ROBOT_PORT, ROBOT_SPEED
from core import registry

MAX_SEC = 5
_host = ROBOT_HOSTS[0]
_DIRS = [   # (регэксп, cmd на Pi, что сказать)
    (r"разверн|разворот|кругом|покрути|крутись", "rotate_left", "Разворачиваюсь."),
    (r"стоп|стой|останов|хватит|тормоз", "stop", "Стою."),
    (r"вп[её]+р[её]д|прямо", "forward", "Еду вперёд."),
    (r"назад|задний ход", "backward", "Еду назад."),
    (r"влево|налево|лев", "left", "Еду влево."),         # «левее», «в левый бок»
    (r"вправо|направо|прав", "right", "Еду вправо."),    # «правее», «в правый бок»
]
_SECONDS = re.compile(r"(\d+(?:[.,]\d+)?)\s*сек")
_NUM_WORDS = {"одну": 1, "одна": 1, "две": 2, "два": 2, "три": 3, "четыре": 4, "пять": 5,
              "пол": 0.5, "полторы": 1.5}
FOLLOWUP_SEC = 30        # столько после команды роботу «назад» без слова «робот» — тоже ему
DIRECTION_WORDS = ["вперёд", "вперед", "впеерёд", "назад", "влево", "вправо", "налево", "направо",
                   "левее", "правее", "стоп", "стой", "развернись", "прямо"]

_timer = None
_lock = threading.Lock()
_last = 0.0              # когда последний раз командовали роботу


def move(cmd: str, speed: int = ROBOT_SPEED):
    """Сначала хост, который ответил в прошлый раз, потом остальные (сеть могла смениться)."""
    global _host
    error = None
    for host in [_host] + [h for h in ROBOT_HOSTS if h != _host]:
        try:
            _post(host, cmd, speed)
            _host = host
            return
        except requests.RequestException as e:
            error = e
    raise error


def _post(host: str, cmd: str, speed: int):
    r = requests.post(f"http://{host}:{ROBOT_PORT}/api/move",
                      json={"cmd": cmd, "speed": speed}, timeout=2)
    r.raise_for_status()


def _stop_later(sec: float):
    global _timer
    with _lock:
        if _timer:
            _timer.cancel()
        _timer = threading.Timer(sec, lambda: _safe_stop())
        _timer.daemon = True
        _timer.start()


def _safe_stop():
    try:
        move("stop")
    except Exception as e:
        print(f"[robot] стоп не прошёл: {e}")


def seconds(text: str) -> float:
    m = _SECONDS.search(text)
    if m:
        sec = float(m.group(1).replace(",", "."))
    else:
        word = re.search(r"(\w+?)\s*секунд", text)            # «две секунды», «полсекунды»
        sec = _NUM_WORDS.get(word.group(1), ROBOT_MOVE_SEC) if word else ROBOT_MOVE_SEC
    return max(0.2, min(MAX_SEC, sec))


@registry.command(
    ["робот", "роботу", "робота", "роботик", "роботом"],
    "Робот: вперёд, назад, влево, вправо, развернись, стоп", "Робот", priority=11,
)
def robot_move(text):
    if "голос" in text.lower():
        return None                       # «голос робота» — смена голоса Кеши
    return _drive(text)


_FOLLOWUP = re.compile(r"\b(?:" + "|".join(DIRECTION_WORDS) + r")\b")


def followup(text):
    """«Кеша, робот вперёд» … «назад на 2 секунды» — слово «робот» второй раз не нужно.
    Вызывает core.handle_command до обычных команд, только FOLLOWUP_SEC после команды роботу."""
    t = text.lower()
    if time.time() - _last > FOLLOWUP_SEC or len(t.split()) > 5 or not _FOLLOWUP.search(t):
        return None
    return _drive(t)


def _drive(text):
    global _last
    t = text.lower()
    for pattern, cmd, said in _DIRS:
        if re.search(pattern, t):
            break
    else:
        return None                       # не движение — пусть разбирается Клод
    try:
        move(cmd)
    except Exception as e:
        print(f"[robot] {e}")
        return "Робот не отвечает. Проверь, включён ли он и заряжен ли."
    _last = time.time()
    if cmd != "stop":
        _stop_later(seconds(t))
    return said
