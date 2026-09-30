"""Мост JS <-> Python."""
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

    @pyqtSlot(str, result=str)
    def send_command(self, text):
        return handle_command(text, source="app")

    @pyqtSlot(str, str, result=str)
    def send_from(self, source, text):
        return handle_command(text, source=source)
