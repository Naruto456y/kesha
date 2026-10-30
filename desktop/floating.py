"""
Плавающий значок реактора (волна 3): маленький круг поверх всех окон.

  • цвет = состояние Кеши (ждёт / слушает / думает / говорит / ошибка);
  • клик — слушать без слова «Кеша» (или выключить звенящий будильник);
  • двойной клик — показать главное окно;
  • правая кнопка — меню (тихий режим, тема, скрыть значок, выход);
  • перетаскивается мышью, место запоминается.
"""
import json
import math
import re
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient, QBrush, QAction
from PyQt6.QtWidgets import QWidget, QMenu, QApplication

import settings
import state_manager

SIZE = 76
STATE_COLORS = {
    "IDLE": "#00E5FF", "WAKE": "#FFFFFF", "LISTENING": "#00FFAA",
    "THINKING": "#FFC400", "SPEAKING": "#3D8BFF", "ERROR": "#FF3355",
}
REACTOR_CONFIG = Path(__file__).parent / "ui" / "reactor_config.js"


def _load_reactor_colors():
    """Те же цвета, что у большого реактора: ui/reactor_config.js из редактора."""
    try:
        m = re.search(r"REACTOR_CONFIG\s*=\s*(\{.*\})\s*;", REACTOR_CONFIG.read_text(encoding="utf-8"), re.S)
        states = json.loads(m.group(1)).get("states", {}) if m else {}
        for name, st in states.items():
            if name in STATE_COLORS and st.get("main"):
                STATE_COLORS[name] = st["main"]
    except Exception as e:
        print(f"[floating] reactor_config.js: {e}")


_load_reactor_colors()
STATE_TIPS = {
    "IDLE": "Кеша ждёт", "WAKE": "Слышу!", "LISTENING": "Слушаю…",
    "THINKING": "Думаю…", "SPEAKING": "Говорю", "ERROR": "Ошибка",
}


class FloatingReactor(QWidget):
    state_changed = pyqtSignal(str)
    setting_changed = pyqtSignal(str)

    def __init__(self, main_window=None):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(SIZE, SIZE)
        self.main_window = main_window
        self.state = state_manager.get_state().value
        self.phase = 0.0
        self._drag_from = None
        self._moved = False

        self.state_changed.connect(self._apply_state)
        self.setting_changed.connect(self._apply_setting)
        self._on_state = self._emit_state
        self._on_setting = self._emit_setting
        state_manager.subscribe(self._on_state)
        settings.subscribe(self._on_setting)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)
        self._place()
        self._apply_state(self.state)

    # ---------- события из других потоков ----------
    def _emit_state(self, payload):
        try:
            self.state_changed.emit(payload.get("state", "IDLE"))
        except RuntimeError:       # виджет уже удалён вместе с окном
            state_manager.unsubscribe(self._on_state)

    def _emit_setting(self, key, _value):
        try:
            self.setting_changed.emit(key)
        except RuntimeError:
            settings.unsubscribe(self._on_setting)

    # ---------- положение ----------
    def _place(self):
        pos = settings.get("float_pos")
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None
        if pos and geo and geo.adjusted(-SIZE, -SIZE, 0, 0).contains(int(pos[0]), int(pos[1])):
            self.move(int(pos[0]), int(pos[1]))
        elif geo:
            self.move(geo.right() - SIZE - 24, geo.bottom() - SIZE - 24)

    # ---------- состояние ----------
    def _apply_state(self, state):
        self.state = state if state in STATE_COLORS else "IDLE"
        self.setToolTip(STATE_TIPS.get(self.state, "Кеша"))
        self.update()

    def _apply_setting(self, key):
        if key == "floating_icon":
            self.setVisible(bool(settings.get("floating_icon")))
        self.update()

    def _tick(self):
        speed = {"LISTENING": 0.16, "THINKING": 0.22, "SPEAKING": 0.12, "WAKE": 0.2}.get(self.state, 0.05)
        self.phase = (self.phase + speed) % (2 * math.pi * 100)
        self.update()

    # ---------- рисование ----------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(STATE_COLORS[self.state])
        center = QPointF(SIZE / 2, SIZE / 2)
        pulse = 0.5 + 0.5 * math.sin(self.phase)
        light = settings.get("theme") == "light"

        glow = QRadialGradient(center, SIZE / 2)
        g = QColor(c)
        g.setAlpha(int(90 + 80 * pulse))
        glow.setColorAt(0.0, g)
        g.setAlpha(0)
        glow.setColorAt(1.0, g)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(center, SIZE / 2, SIZE / 2)

        p.setBrush(QColor("#EAF6FF" if light else "#0A2432"))
        p.drawEllipse(center, SIZE * 0.33, SIZE * 0.33)

        pen = QPen(c, 3)
        pen.setDashPattern([3, 2.5])
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.translate(center)
        p.rotate(math.degrees(self.phase) % 360)
        p.drawEllipse(QPointF(0, 0), SIZE * 0.36, SIZE * 0.36)
        p.restore()

        core = QRadialGradient(center, SIZE * 0.2)
        core.setColorAt(0.0, QColor("#FFFFFF"))
        core.setColorAt(1.0, c)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(core))
        r = SIZE * (0.16 + 0.03 * pulse)
        p.drawEllipse(center, r, r)
        p.end()

    # ---------- мышь ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_from = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._moved = False

    def mouseMoveEvent(self, e):
        if self._drag_from is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_from)
            self._moved = True

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self._moved:
            settings.set("float_pos", [self.x(), self.y()])
        else:
            self._listen()
        self._drag_from = None

    def mouseDoubleClickEvent(self, _e):
        self._show_main()

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        show = QAction("Показать окно", menu, triggered=lambda *_: self._show_main())
        listen = QAction("Слушать (Ctrl+Space)", menu, triggered=lambda *_: self._listen())
        silent = QAction("Тихий режим", menu, checkable=True, checked=bool(settings.get("silent")),
                         triggered=lambda on: settings.set("silent", on))
        light = QAction("Светлая тема", menu, checkable=True, checked=settings.get("theme") == "light",
                        triggered=lambda on: settings.set("theme", "light" if on else "dark"))
        hide = QAction("Скрыть значок", menu, triggered=lambda *_: settings.set("floating_icon", False))
        quit_ = QAction("Выход", menu, triggered=lambda *_: QApplication.quit())
        for a in (show, listen, silent, light, hide):
            menu.addAction(a)
        menu.addSeparator()
        menu.addAction(quit_)
        menu.exec(e.globalPos())

    def _listen(self):
        try:
            from voice import arm
            arm()
        except Exception as ex:
            print("[floating] голос недоступен:", ex)

    def _show_main(self):
        w = self.main_window
        if w is not None:
            w.showNormal()
            w.raise_()
            w.activateWindow()
