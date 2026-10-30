"""Десктоп-приложение Кеша."""
import json
import os
import sys
from pathlib import Path
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QIcon
import settings
from config import DESKTOP_WIDTH, DESKTOP_HEIGHT, DESKTOP_TITLE, ICON_PATH
from .bridge import Bridge


class KeshaWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(DESKTOP_TITLE)
        self.resize(DESKTOP_WIDTH, DESKTOP_HEIGHT)
        if os.path.exists(ICON_PATH):
            try: self.setWindowIcon(QIcon(ICON_PATH))
            except Exception: pass
        self.view = QWebEngineView()
        self.setCentralWidget(self.view)
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
        # всё из Python в страницу идёт одним путём — runJavaScript (без дублей)
        self.bridge.core_event.connect(lambda s, t, r: self._js("onCoreEvent", s, t, r))
        self.bridge.state_event.connect(lambda st, t: self._js("onState", st, t))
        self.bridge.setting_event.connect(lambda k, v: self._js("onSetting", k, json.loads(v)))
        self.view.loadFinished.connect(self._on_loaded)
        ui = Path(__file__).parent / "ui" / "index.html"
        self.view.load(QUrl.fromLocalFile(str(ui)))

    def _js(self, fn, *args):
        params = ",".join(json.dumps(a, ensure_ascii=False) for a in args)
        self.view.page().runJavaScript(f"if(window.{fn}){fn}({params});")

    def _on_loaded(self, ok):
        if ok:
            self._js("onSetting", "theme", settings.get("theme"))
            import state_manager
            self._js("onState", state_manager.get_state().value, "")


def start_desktop():
    app = QApplication(sys.argv)
    w = KeshaWindow()
    w.show()
    floating = None
    try:
        from .floating import FloatingReactor
        floating = FloatingReactor(main_window=w)
        floating.setVisible(bool(settings.get("floating_icon")))
    except Exception as e:
        print("[desktop] плавающий значок недоступен:", e)
    app._kesha_floating = floating   # держим ссылку, чтобы виджет не собрал GC
    sys.exit(app.exec())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    start_desktop()
