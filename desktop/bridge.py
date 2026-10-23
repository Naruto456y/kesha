"""Мост JS <-> Python."""
import threading
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from core import handle_command, subscribe


class Bridge(QObject):
    core_event = pyqtSignal(str, str, str)

    def __init__(self):
        super().__init__()
        subscribe(self._on_event)

    def _on_event(self, source, text, response):
        try:
            self.core_event.emit(source, text, response)
        except Exception as e:
            print("[bridge]", e)

    @staticmethod
    def _run(text, source):
        # результат приходит в UI через core_event; вызов в отдельном потоке, чтобы окно не замирало
        threading.Thread(target=handle_command, args=(text, source), daemon=True).start()

    @pyqtSlot(str)
    def send_command(self, text):
        self._run(text, "app")

    @pyqtSlot(str, str)
    def send_from(self, source, text):
        self._run(text, source)
