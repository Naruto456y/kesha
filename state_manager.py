"""
Глобальное состояние Кеши + рассылка событий (внутренние подписчики и WebSocket).

Подписчик:     callback(payload: dict)
WS-эмиттер:    fn(payload: dict) — обычная или async функция, которая шлёт JSON в сокеты.

Подключение к FastAPI (пример):
    import asyncio, state_manager

    @app.on_event("startup")
    async def _hook():
        state_manager.register_ws_emitter(ws_manager.broadcast, loop=asyncio.get_running_loop())

payload = {"type": "state", "state": "LISTENING", "prev": "IDLE", "info": {...}, "ts": 1234.5}
"""
import asyncio
import inspect
import threading
import time
from enum import Enum


class State(str, Enum):
    IDLE = "IDLE"
    WAKE = "WAKE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


_lock = threading.RLock()
_state = State.IDLE
_info = {}
_subscribers = []
_ws_emitters = []   # [(fn, loop)]


def get_state():
    return _state


def get_info():
    with _lock:
        return dict(_info)


def snapshot():
    """Текущее состояние в формате payload (удобно отправить новому WS-клиенту)."""
    with _lock:
        return {"type": "state", "state": _state.value, "prev": None,
                "info": dict(_info), "ts": time.time()}


def subscribe(callback):
    if callback not in _subscribers:
        _subscribers.append(callback)


def unsubscribe(callback):
    if callback in _subscribers:
        _subscribers.remove(callback)


def register_ws_emitter(fn, loop=None):
    """Зарегистрировать функцию рассылки в WebSocket.
    Для async-функций передай loop (event loop FastAPI) — тогда вызов безопасен из любого потока."""
    with _lock:
        _ws_emitters[:] = [e for e in _ws_emitters if e[0] is not fn]
        _ws_emitters.append((fn, loop))


def unregister_ws_emitter(fn):
    with _lock:
        _ws_emitters[:] = [e for e in _ws_emitters if e[0] is not fn]


def set_state(new_state, **info):
    """Сменить состояние и разослать событие. Возвращает True, если что-то изменилось."""
    global _state, _info
    new_state = State(new_state)
    with _lock:
        old = _state
        if new_state == old and not info:
            return False
        _state, _info = new_state, dict(info)
        payload = {"type": "state", "state": new_state.value, "prev": old.value,
                   "info": dict(info), "ts": time.time()}
    _dispatch(payload)
    return True


async def _await(aw):
    await aw


def _run_awaitable(aw, loop):
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(_await(aw), loop)
        return
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_await(aw))
    else:
        running.create_task(_await(aw))


def _dispatch(payload):
    for cb in list(_subscribers):
        try:
            cb(payload)
        except Exception as e:
            print(f"[state] ошибка подписчика {cb}: {e}")
    for fn, loop in list(_ws_emitters):
        try:
            res = fn(payload)
            if inspect.isawaitable(res):
                _run_awaitable(res, loop)
        except Exception as e:
            print(f"[state] ошибка WS-эмиттера {fn}: {e}")
