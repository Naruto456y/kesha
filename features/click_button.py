"""
«Кеша, нажми кнопку ОК» — найти на экране кнопку по названию и нажать её.

1. UI Automation (pywinauto): берём элементы активного окна (кнопки, пункты меню, ссылки,
   вкладки…) и сравниваем их названия с услышанным. Точно и не зависит от того, где окно.
2. Если UIA ничего не дал (игры, картинки, canvas) — OCR через ScreenReader из pycraft-tools.
   Он тяжёлый (easyocr), поэтому только если установлен.
"""
import os
import re
import threading

from core import registry

CLICKABLE = ("Button", "SplitButton", "MenuItem", "Hyperlink", "TabItem", "ListItem",
             "CheckBox", "RadioButton", "TreeItem")
MIN_SCORE = 80          # rapidfuzz 0..100: ниже — «не нашёл», а не жмём что попало
MAX_ELEMENTS = 1500     # в огромных окнах (браузер) не обходим дерево бесконечно

# голосом говорят «ок», а на кнопке «OK»; «крестик» — кнопка закрытия
ALIASES = {
    "ок": ["ok", "ок", "окей"], "окей": ["ok", "ок"], "ok": ["ok", "ок"],
    "да": ["да", "yes"], "нет": ["нет", "no"], "отмена": ["отмена", "cancel"],
    "закрыть": ["закрыть", "close"], "крестик": ["закрыть", "close"],
    "применить": ["применить", "apply"], "далее": ["далее", "next"], "назад": ["назад", "back"],
    "готово": ["готово", "done", "finish"], "сохранить": ["сохранить", "save"],
    "свернуть": ["свернуть", "minimize"], "развернуть": ["развернуть", "maximize"],
}
FILLER = re.compile(r"^(?:на|по|кнопк[уаеи]|кнопочк[уаеи]|пункт|ссылк[уе]|вкладк[уе])\s+")


def normalize(s):
    s = (s or "").lower().replace("ё", "е").replace("&", "")
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def clean_target(spoken):
    """«на кнопку ок» -> «ок»."""
    t = normalize(spoken)
    while True:
        new = FILLER.sub("", t)
        if new == t:
            return t
        t = new


def score(target, name):
    """Насколько название элемента похоже на услышанное, 0..100."""
    name = normalize(name)
    if not name or not target:
        return 0
    variants = ALIASES.get(target, [target])
    best = 0
    for v in variants:
        if name == v:
            return 100
        if name.startswith(v + " ") or name.endswith(" " + v):
            best = max(best, 92)
        try:
            from rapidfuzz import fuzz
            best = max(best, fuzz.ratio(v, name), fuzz.partial_ratio(v, name) - 10 if len(v) > 3 else 0)
        except ImportError:
            import difflib
            best = max(best, int(difflib.SequenceMatcher(None, v, name).ratio() * 100))
    return best


def best_match(target, elements):
    """elements: [(name, obj)] -> (obj, name, score) лучшего или None."""
    found = None
    for name, obj in elements:
        s = score(target, name)
        if s >= MIN_SCORE and (found is None or s > found[2]):
            found = (obj, name, s)
            if s == 100:
                break
    return found


# ---------- UI Automation ----------

def _foreground_windows(desktop):
    """Активное окно первым, потом остальные видимые (кроме окон самой Кеши)."""
    import ctypes
    own = {os.getpid()}
    try:
        import psutil
        own |= {p.pid for p in psutil.Process().children(recursive=True)}
    except Exception:
        pass
    fg = ctypes.windll.user32.GetForegroundWindow()
    wins = [w for w in desktop.windows() if w.is_visible() and w.process_id() not in own]
    wins.sort(key=lambda w: w.handle != fg)
    return wins[:5]


def _elements(win):
    out = []
    for el in win.descendants():
        if len(out) >= MAX_ELEMENTS:
            break
        try:
            if el.element_info.control_type in CLICKABLE and el.is_visible() and el.is_enabled():
                name = el.window_text()
                if name:
                    out.append((name, el))
        except Exception:
            continue
    return out


def _press(el):
    try:
        el.invoke()              # нажатие через UIA, без движения мыши
        return
    except Exception:
        pass
    el.click_input()


def click_uia(target):
    """-> название нажатого элемента или None."""
    from pywinauto import Desktop
    desktop = Desktop(backend="uia")
    for win in _foreground_windows(desktop):
        hit = best_match(target, _elements(win))
        if hit:
            el, name, _ = hit
            try:
                win.set_focus()
            except Exception:
                pass
            _press(el)
            return name
    return None


# ---------- OCR (запасной путь) ----------

def click_ocr(target):
    import contextlib
    import io
    try:
        from help_manager import ScreenReader
    except Exception:
        return None
    for v in ALIASES.get(target, [target]):
        with contextlib.redirect_stdout(io.StringIO()):
            res = ScreenReader.find_text_coordinates(v, languages=["ru", "en"], confidence_threshold=0.4)
        if res and res.get("found"):
            import mouse
            mouse.move(res["x"], res["y"])
            mouse.click("left")
            return v
    return None


def click_by_name(spoken):
    """-> (ok, ответ для пользователя)."""
    target = clean_target(spoken)
    if not target:
        return False, "Какую кнопку нажать?"
    try:
        name = click_uia(target)
    except ImportError:
        name = None
    except Exception as e:
        print(f"[click_button] UIA: {e}")
        name = None
    if not name:
        name = click_ocr(target)
    if name:
        return True, f"Нажал «{name}»"
    return False, f"Не нашёл кнопку «{target}»"


def _extract(text, words):
    t = normalize(text)
    for w in sorted(words, key=len, reverse=True):
        m = re.search(rf"(?<!\w){re.escape(normalize(w))}(?!\w)", t)
        if m:
            return t[m.end():].strip()
    return ""


WORDS = ["кликни по кнопке", "кликни на кнопку", "кликни кнопку", "щелкни по кнопке",
         "щёлкни по кнопке", "щелкни на кнопку", "щёлкни на кнопку", "нажми кнопочку",
         "нажми на кнопочку", "ткни на кнопку", "ткни кнопку"]


@registry.command(WORDS, "Нажать кнопку по названию", "Система", priority=7)
def click_button(text):
    target = _extract(text, WORDS)
    if not target:
        return "Какую кнопку нажать?"
    return click_by_name(target)[1]
