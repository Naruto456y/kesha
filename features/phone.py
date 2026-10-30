"""
«Где мой телефон» — заставить телефон зазвонить через «Связь с телефоном» (Phone Link).

Как руками: открыть приложение -> значок телефона со звуком -> «Воспроизвести звук».
Жмём те же кнопки через UI Automation (pywinauto), а не по координатам: окно может стоять где угодно.
"""
import subprocess
import threading
import time

from core import registry

APP = r"shell:AppsFolder\Microsoft.YourPhone_8wekyb3d8bbwe!App"
RING_ICON = "RingMyPhoneIndicatorToggleButton"     # значок «телефон со звуком» в шапке
RING_BUTTON = "Воспроизвести звук"                 # кнопка во всплывающем окне


def _window(desktop, timeout):
    end = time.time() + timeout
    while time.time() < end:
        for w in desktop.windows():
            if "телефон" in w.window_text().lower() or "phone link" in w.window_text().lower():
                return w
        time.sleep(0.4)
    return None


def _button(win, timeout, auto_id=None, name=None):
    end = time.time() + timeout
    while time.time() < end:
        for b in win.descendants(control_type="Button"):
            if (auto_id and b.element_info.automation_id == auto_id) or (name and b.window_text() == name):
                return b
        time.sleep(0.3)
    return None


def ring_phone():
    """-> None, если зазвонил, иначе причина."""
    from pywinauto import Desktop
    subprocess.Popen(["explorer.exe", APP])           # уже открыто — просто выйдет вперёд
    desktop = Desktop(backend="uia")
    win = _window(desktop, 15)
    if win is None:
        return "не открылась «Связь с телефоном»"
    icon = _button(win, 10, auto_id=RING_ICON)
    if icon is None:
        return "телефон не подключён к «Связи с телефоном»"
    win.set_focus()
    icon.click_input()
    button = _button(win, 5, name=RING_BUTTON)
    if button is None:
        return "не нашёл кнопку «Воспроизвести звук»"
    button.click_input()
    return None


def _ring_async():
    try:
        why = ring_phone()
    except Exception as e:
        why = str(e)
    if why:
        print(f"[phone] {why}")
        from voice import say
        say(f"Не получилось: {why}.")


@registry.command(
    ["найди телефон", "найди мой телефон", "где телефон", "где мой телефон", "потерял телефон",
     "я потерял телефон", "не могу найти телефон", "поищи телефон", "пусть телефон зазвонит",
     "позвони на мой телефон", "прозвони телефон", "звук на телефоне", "найти телефон"],
    "Найти телефон (зазвонит)", "Специальные", priority=30,
)
def find_phone(text):
    threading.Thread(target=_ring_async, daemon=True, name="find-phone").start()
    return "Ищу телефон, сейчас зазвонит."
