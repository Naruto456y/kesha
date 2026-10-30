"""
Персонализация по времени (волна 5): утром «Доброе утро», вечером «Добрый вечер».
"""

import random
from datetime import datetime

_GREET = {               # одна фраза, без «как дела» и «пора спать»
    "morning": ["Доброе утро!"],
    "day":     ["Добрый день!", "Привет!"],
    "evening": ["Добрый вечер!"],
    "night":   ["Доброй ночи!"],
}


def part_of_day(now: datetime) -> str:
    h = now.hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 18:
        return "day"
    if 18 <= h < 23:
        return "evening"
    return "night"


def greeting(now: "datetime | None" = None) -> str:
    return random.choice(_GREET[part_of_day(now or datetime.now())])


def startup_phrase(now: "datetime | None" = None) -> str:
    return f"{greeting(now)} Готов к работе."
