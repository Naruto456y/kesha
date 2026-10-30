"""Мост JS <-> Python."""
import json
import threading

from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal

import settings
import state_manager
from core import handle_command, subscribe


class Bridge(QObject):
    core_event = pyqtSignal(str, str, str)     # источник, текст, ответ
    state_event = pyqtSignal(str, str)         # состояние реактора, текст
    setting_event = pyqtSignal(str, str)       # ключ, значение (JSON)

    def __init__(self):
        super().__init__()
        subscribe(self._on_event)
        state_manager.subscribe(self._on_state)
        settings.subscribe(self._on_setting)

    def _on_event(self, source, text, response):
        try:
            self.core_event.emit(source, text, response)
        except RuntimeError:       # окно закрыто, Qt-объект удалён
            self._detach()
        except Exception as e:
            print("[bridge]", e)

    def _on_state(self, payload):
        info = payload.get("info") or {}
        text = str(info.get("text") or info.get("error") or "")
        try:
            self.state_event.emit(payload.get("state", "IDLE"), text)
        except RuntimeError:
            self._detach()
        except Exception as e:
            print("[bridge]", e)

    def _on_setting(self, key, value):
        try:
            self.setting_event.emit(key, json.dumps(value, ensure_ascii=False))
        except RuntimeError:
            self._detach()
        except Exception as e:
            print("[bridge]", e)

    def _detach(self):
        """Окно закрыли — больше не слушаем ядро, иначе каждое событие печатает ошибку."""
        from core import unsubscribe
        unsubscribe(self._on_event)
        state_manager.unsubscribe(self._on_state)
        settings.unsubscribe(self._on_setting)

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

    @pyqtSlot()
    def listen_now(self):
        """Кнопка «СЛУШАТЬ»: микрофон без слова «Кеша»."""
        try:
            from voice import arm
            arm()
        except Exception as e:
            print("[bridge] голос недоступен:", e)

    @pyqtSlot()
    def open_reactor_editor(self):
        """Кнопка «РЕАКТОР»: редактор цветов в браузере."""
        import os
        from pathlib import Path
        os.startfile(str(Path(__file__).parent / "ui" / "reactor_editor.html"))

    @pyqtSlot(result=str)
    def get_commands(self):
        """Команды из реестра для правой панели: [{category, items: [{name, desc}]}]."""
        from core import registry
        cats = {}
        for c in registry.commands:
            cats.setdefault(c["category"], []).append(
                {"name": c["patterns"][0] if c["patterns"] else c["name"],
                 "desc": c["description"], "risky": bool(c.get("risky"))})
        return json.dumps([{"category": k, "items": v} for k, v in cats.items()],
                          ensure_ascii=False)

    @pyqtSlot(result=str)
    def get_settings(self):
        return json.dumps(settings.all_settings(), ensure_ascii=False)

    @pyqtSlot(str, str)
    def set_setting(self, key, value_json):
        try:
            settings.set(key, json.loads(value_json))
        except Exception as e:
            print("[bridge] set_setting:", e)
