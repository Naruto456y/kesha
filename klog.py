"""
Лог непонятных фраз (волна 2): logs/kesha.log.

Формат строки:  время | ТИП | источник | что сказал пользователь | детали
Типы:
  UNKNOWN  — ни одна команда не подошла (смотри сюда, чтобы добавить паттерны)
  AI_CMD   — GigaChat перефразировал фразу в команду
  FUZZY    — поймали по нечёткому совпадению (опечатка/искажение STT)
  SYNONYM  — поймали через синонимы
  FOLLOWUP — уточнение по контексту («а в Питере?»)
Частые FUZZY/AI_CMD/UNKNOWN фразы — кандидаты в паттерны команд.
"""

import logging
from logging.handlers import RotatingFileHandler

from config import UNKNOWN_LOG_FILE

_log = logging.getLogger("kesha.phrases")
_log.setLevel(logging.INFO)
_log.propagate = False   # не дублировать в root-логгер (telegram_bot его настраивает)
_handler = None


def set_path(path):
    """Перенаправить лог в другой файл (для тестов)."""
    global _handler
    if _handler is not None:
        _log.removeHandler(_handler)
        _handler.close()
    _handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
    _log.addHandler(_handler)


def phrase(kind: str, source: str, text: str, detail: str = ""):
    if _handler is None:
        set_path(UNKNOWN_LOG_FILE)
    one_line = lambda s: " ".join(str(s).split())
    _log.info("%s | %s | %s | %s", kind, source, one_line(text), one_line(detail))
