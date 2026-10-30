"""
Яндекс Музыка: нажать жёлтую кнопку «играть» на странице, когда Кеша её открыла.

Ищем кнопку на экране через ScreenReader из HelpManager (поиск по картинке).
Шаблоны — внутренний квадрат кнопки (жёлтое + чёрный треугольник), чтобы фон страницы
не мешал; сделаны в нескольких масштабах под разные экраны (Media/yamusic/play_*.png).
Если на кнопке пауза (музыка уже играет), шаблон не совпадёт и ничего не нажмётся.
"""
import contextlib
import io
import threading
import time
from pathlib import Path

TEMPLATES = sorted((Path(__file__).resolve().parent.parent / "Media" / "yamusic").glob("play_*.png"),
                   key=lambda p: int(p.stem.split("_")[1]))
CONFIDENCE = 0.85


def find_play_button():
    """-> (x, y) центра кнопки на экране или None. Ничего не нажимает."""
    from help_manager import ScreenReader
    for tpl in TEMPLATES:
        with contextlib.redirect_stdout(io.StringIO()):      # ScreenReader пишет в консоль каждую попытку
            pos = ScreenReader.find_image(str(tpl), CONFIDENCE)
        if pos:
            return pos
    return None


def click_play(timeout=25.0, interval=0.7):
    """Ждёт появления кнопки до timeout секунд и нажимает. -> True, если нажала."""
    import pyautogui
    deadline = time.time() + timeout
    time.sleep(2.0)                           # страница только открывается
    while time.time() < deadline:
        try:
            pos = find_play_button()
        except Exception as e:
            print(f"[yamusic] поиск кнопки: {e}")
            return False
        if pos:
            pyautogui.click(*pos)
            print(f"[yamusic] нажала «играть» в {pos}")
            return True
        time.sleep(interval)
    print("[yamusic] кнопка «играть» не появилась")
    return False


def click_play_async(**kw):
    """Не задерживает ответ Кеши: ищет кнопку в фоне."""
    t = threading.Thread(target=click_play, kwargs=kw, daemon=True, name="yamusic")
    t.start()
    return t


# ---------- проверка по логотипу ----------
LOGO = TEMPLATES[0].parent / "logo.png" if TEMPLATES else Path("Media/yamusic/logo.png")
LOGO_SCALES = tuple(round(0.5 * 1.12 ** i, 3) for i in range(14))   # 0.5…2.2 с шагом 12%: промежуточные размеры тоже ловятся
LOGO_SCORE = 0.7      # полный логотип на любом фоне даёт ~0.95+, жёлтая кнопка «играть» и одна звёздочка — заметно ниже
_logo_mask = None


def _yellow_mask(bgr):
    """Жёлтый цвет Яндекса -> float-маска 0..1: форма логотипа не зависит от фона страницы."""
    import cv2
    import numpy as np
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (20, 120, 170), (36, 255, 255)).astype(np.float32) / 255.0
    return cv2.GaussianBlur(m, (3, 3), 0)


def logo_score(screen_bgr):
    """Лучшее совпадение логотипа-звёздочки на кадре (0..1). Ищем по форме жёлтого,
    а не по пикселям: фон страницы светлый или тёмный — неважно. Круглая жёлтая кнопка
    «играть» на логотип не похожа и даёт низкую оценку."""
    import cv2
    global _logo_mask
    if _logo_mask is None:
        _logo_mask = _yellow_mask(cv2.imread(str(LOGO)))
    scene = _yellow_mask(screen_bgr)
    if scene.max() == 0:
        return 0.0
    best = 0.0
    for s in LOGO_SCALES:
        t = cv2.resize(_logo_mask, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        if t.shape[0] >= scene.shape[0] or t.shape[1] >= scene.shape[1] or t.std() == 0:
            continue
        best = max(best, float(cv2.minMaxLoc(cv2.matchTemplate(scene, t, cv2.TM_CCOEFF_NORMED))[1]))
    return best


def logo_visible():
    """На экране сейчас виден логотип Яндекс Музыки."""
    try:
        import cv2
        import numpy as np
        import pyautogui
        shot = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
        return logo_score(shot) >= LOGO_SCORE
    except Exception as e:
        print(f"[yamusic] проверка логотипа: {e}")
        return False
