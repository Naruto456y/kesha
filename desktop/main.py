"""Десктоп-приложение Кеша."""
import sys, os
from pathlib import Path
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QIcon
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
        self.bridge.core_event.connect(self._forward)
        ui = Path(__file__).parent / "ui" / "index.html"
        self.view.load(QUrl.fromLocalFile(str(ui)))

    def _forward(self, source, text, response):
        def esc(s):
            return (s.replace("\\", "\\\\")
                     .replace("'", "\\'")
                     .replace("\n", "\\n")
                     .replace("\r", ""))
        js = "if(window.onCoreEvent)onCoreEvent('%s','%s','%s');" % (
            esc(source), esc(text), esc(response))
        self.view.page().runJavaScript(js)


def start_desktop():
    app = QApplication(sys.argv)
    w = KeshaWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    start_desktop()
