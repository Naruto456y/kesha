"""
Фичи волн 3–5. Импорт пакета регистрирует их команды в core.registry.

    import features
    features.start_background()   # фоновые службы (напоминания)
"""

from . import modes, reminders, notes, stats, rates, agenda, messenger, utilities, yamusic, web, phone, robot  # noqa: F401


def start_background():
    reminders.start()
