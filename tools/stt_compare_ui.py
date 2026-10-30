"""Aqua Voice vs GigaAM: python tools/stt_compare_ui.py
Вкладка «Тест команд»: читаешь фразы вслух, запись и проверка идут сами, видно, какая команда Кеши сработала.
Вкладка «Свободная речь»: говоришь что угодно, видишь оба текста и сработавшую команду.
Токен вводится в поле (Ctrl+V), нигде не сохраняется."""
import collections
import os
import queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pygame
import sounddevice as sd

import aqua_stt
from stt_phrases import PHRASES

SR = 16000
BLOCK = 800                      # 50 мс
SILENCE_END = 18                 # блоков тишины после речи (0,9 с)
WAIT_SPEECH = 9.0
MAX_SPEECH = 9.0

BG, PANEL, PANEL2 = (18, 20, 27), (30, 33, 43), (40, 44, 57)
FG, DIM, LINE = (236, 238, 246), (128, 135, 156), (55, 60, 76)
GREEN, BLUE, VIOLET = (62, 190, 120), (82, 140, 235), (150, 105, 235)
RED, YELLOW = (225, 85, 85), (235, 190, 70)

pygame.init()
W, H = 1160, 740
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Кеша: Aqua Voice vs GigaAM")


def font(size, bold=False):
    for name in ("segoeui", "arial", "tahoma"):
        f = pygame.font.SysFont(name, size, bold=bold)
        if f:
            return f
    return pygame.font.Font(None, size)


F, FS, FB, FH, FXS = font(20), font(16), font(21, True), font(38, True), font(14)

S = {
    "token": os.environ.get("AQUA_API_KEY", ""), "focus": False, "show": False,
    "tab": "test", "giga": None, "norm": None, "match": None,
    "giga_state": "грузится…", "cmd_state": "грузятся…",
    "running": False, "skip": False, "abort": False, "idx": 0,
    "phase": "idle", "msg": "Нажми «Старт» и читай фразы вслух.", "level": 0.0,
    "results": {},                # idx -> {"giga": r, "aqua": r}
    "free": None,                 # результат вкладки «свободная речь»
    "list_scroll": 0,
}
LOCK = threading.Lock()


# ---------------------------------------------------------------- движки
def load_backend():
    def giga():
        try:
            from voice.gigaam_recognizer import GigaAMRecognizer, normalize
            S["giga"], S["norm"] = GigaAMRecognizer(), normalize
            S["giga_state"] = "готов"
        except Exception as e:
            S["giga_state"] = f"ошибка: {str(e)[:40]}"

    def cmds():
        try:
            import commands  # noqa: F401
            import features  # noqa: F401
            from core import _matching
            S["match"] = _matching
            S["cmd_state"] = "загружены"
        except Exception as e:
            S["cmd_state"] = f"ошибка: {str(e)[:40]}"

    threading.Thread(target=giga, daemon=True).start()
    threading.Thread(target=cmds, daemon=True).start()


def norm(t):
    return S["norm"](t) if S["norm"] else (t or "").lower()


def matched(text):
    if not S["match"] or not text:
        return []
    try:
        return [c["name"] for c in S["match"](norm(text))]
    except Exception:
        return []


def run_engine(name, pcm, out):
    t0 = time.time()
    try:
        if name == "giga":
            if S["giga"] is None:
                raise RuntimeError("GigaAM ещё грузится")
            text = S["giga"].recognize(pcm, normalize_text=False)
        else:
            os.environ["AQUA_API_KEY"] = S["token"].strip()
            aqua_stt._client = None
            text = aqua_stt.stt_pcm(pcm, SR, "ru")
        out[name] = {"text": text, "ms": int((time.time() - t0) * 1000), "err": "", "cmds": matched(text)}
    except Exception as e:
        out[name] = {"text": "", "ms": int((time.time() - t0) * 1000),
                     "err": f"{type(e).__name__}: {str(e)[:150]}", "cmds": []}


def recognize_both(pcm):
    out = {}
    ths = [threading.Thread(target=run_engine, args=(n, pcm, out)) for n in ("giga", "aqua")]
    [t.start() for t in ths]
    [t.join() for t in ths]
    return out


# ---------------------------------------------------------------- запись с автостопом
def capture():
    """Ждёт начала речи и пишет до паузы. None — не дождались / отменили."""
    q = queue.Queue()

    def cb(indata, frames, t, status):
        q.put(indata[:, 0].copy())

    pre = collections.deque(maxlen=6)
    buf, noise, started, quiet = [], [], False, 0
    t0 = time.time()
    S["phase"] = "listen"
    with sd.InputStream(samplerate=SR, channels=1, dtype="int16", blocksize=BLOCK, callback=cb):
        while True:
            if S["abort"] or S["skip"] or time.time() - t0 > WAIT_SPEECH + MAX_SPEECH:
                return None
            try:
                blk = q.get(timeout=0.2)
            except queue.Empty:
                continue
            rms = float(np.sqrt(np.mean(blk.astype(np.float32) ** 2)))
            S["level"] = rms
            if len(noise) < 6:
                noise.append(rms)
                pre.append(blk)
                continue
            thr = max(450.0, float(np.median(noise)) * 3.5)
            if not started:
                pre.append(blk)
                if rms > thr:
                    started, buf, t_speech = True, list(pre), time.time()
                    S["phase"] = "speech"
                elif time.time() - t0 > WAIT_SPEECH:
                    return None
            else:
                buf.append(blk)
                quiet = quiet + 1 if rms < thr else 0
                if quiet >= SILENCE_END or time.time() - t_speech > MAX_SPEECH:
                    break
    S["level"] = 0.0
    pcm = np.concatenate(buf).tobytes()
    return pcm if len(pcm) > SR * 2 * 0.25 else None


# ---------------------------------------------------------------- сценарии
def test_loop():
    S["running"], S["abort"] = True, False
    while S["running"] and S["idx"] < len(PHRASES):
        i = S["idx"]
        S["skip"] = False
        S["msg"] = "Читай фразу вслух"
        pcm = capture()
        if S["abort"]:
            break
        if pcm is None:
            if not S["skip"]:
                S["results"][i] = {"giga": None, "aqua": None, "silent": True}
            S["idx"] += 1
            continue
        S["phase"] = "recog"
        S["msg"] = "Распознаю…"
        res = recognize_both(pcm)
        S["results"][i] = res
        S["phase"] = "show"
        S["msg"] = "Следующая фраза через секунду…"
        t = time.time()
        while time.time() - t < 1.4 and not S["abort"] and not S["skip"]:
            time.sleep(0.05)
        S["idx"] += 1
    S["running"] = False
    S["phase"] = "idle"
    S["msg"] = "Тест окончен." if S["idx"] >= len(PHRASES) else "Пауза."


def free_once():
    S["running"], S["abort"], S["skip"] = True, False, False
    S["free"] = None
    S["msg"] = "Говори…"
    pcm = capture()
    if pcm is None:
        S["msg"] = "Речь не услышана."
    else:
        S["phase"], S["msg"] = "recog", "Распознаю…"
        S["free"] = recognize_both(pcm)
        S["msg"] = "Готово. Можно ещё раз."
    S["running"], S["phase"] = False, "idle"


def spawn(fn):
    if not S["running"]:
        if S["tab"] == "test" or fn is free_once:
            if not S["token"].strip():
                S["msg"] = "Сначала введи токен Aqua в поле сверху."
                return
        threading.Thread(target=fn, daemon=True).start()


def verdict(idx, eng):
    """True / False / None (нет данных)."""
    r = S["results"].get(idx)
    if not r or r.get("silent") or not r.get(eng):
        return None
    return PHRASES[idx][1] in r[eng]["cmds"]


def score(eng):
    ok = tot = 0
    ms = []
    for i in S["results"]:
        v = verdict(i, eng)
        if v is None:
            continue
        tot += 1
        ok += v
        ms.append(S["results"][i][eng]["ms"])
    return ok, tot, (sum(ms) // len(ms) if ms else 0)


# ---------------------------------------------------------------- отрисовка
def rr(rect, color, r=10, w=0):
    pygame.draw.rect(screen, color, rect, w, border_radius=r)


def txt(s, f, color, pos, center=False):
    img = f.render(s, True, color)
    screen.blit(img, img.get_rect(center=pos) if center else pos)
    return img.get_width()


def wrap(text, f, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if f.size(t)[0] <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def button(rect, label, color, enabled=True):
    mouse = pygame.mouse.get_pos()
    c = color if enabled else PANEL2
    if enabled and rect.collidepoint(mouse):
        c = tuple(min(255, v + 25) for v in color)
    rr(rect, c)
    txt(label, FB, (255, 255, 255) if enabled else DIM, rect.center, center=True)


def result_card(rect, title, color, r, expected=None):
    rr(rect, PANEL)
    pygame.draw.rect(screen, color, (rect.x, rect.y + 10, 4, rect.h - 20), border_radius=2)
    txt(title, FB, color, (rect.x + 20, rect.y + 12))
    if not r:
        txt("— ждёт —", FS, DIM, (rect.x + 20, rect.y + 52))
        return
    txt(f"{r['ms']} мс", FS, DIM, (rect.right - 82, rect.y + 16))
    if r["err"]:
        for i, l in enumerate(wrap(r["err"], FS, rect.w - 40)[:4]):
            txt(l, FS, RED, (rect.x + 20, rect.y + 52 + i * 22))
        return
    for i, l in enumerate(wrap(r["text"] or "(пусто)", F, rect.w - 40)[:3]):
        txt(l, F, FG, (rect.x + 20, rect.y + 50 + i * 26))
    y = rect.bottom - 54
    if expected:
        ok = expected in r["cmds"]
        txt("ВЕРНО: команда сработает" if ok else "ОШИБКА: не та команда", FB, GREEN if ok else RED, (rect.x + 20, y))
        got = r["cmds"][0] if r["cmds"] else "ничего"
        txt(f"нашлось: {got}", FXS, DIM, (rect.x + 20, y + 28))
    else:
        got = ", ".join(r["cmds"][:3]) or "команда не найдена"
        txt(f"сработает: {got}", FS, GREEN if r["cmds"] else YELLOW, (rect.x + 20, y + 14))


TOKEN_RECT, EYE_RECT = pygame.Rect(360, 20, 500, 40), pygame.Rect(870, 20, 100, 40)
TAB_TEST, TAB_FREE = pygame.Rect(20, 84, 170, 38), pygame.Rect(200, 84, 200, 38)
BTN_START = pygame.Rect(400, 612, 190, 52)
BTN_SKIP = pygame.Rect(604, 612, 170, 52)
BTN_RESET = pygame.Rect(788, 612, 170, 52)
BTN_FREE = pygame.Rect(400, 612, 300, 52)
LIST_RECT = pygame.Rect(20, 156, 350, 564)


def draw_header():
    txt("Aqua Voice  vs  GigaAM", FB, FG, (20, 28))
    txt("Токен Aqua", FXS, DIM, (360, 4))
    rr(TOKEN_RECT, PANEL)
    rr(TOKEN_RECT, BLUE if S["focus"] else LINE, w=2)
    tok = S["token"] if S["show"] else "•" * len(S["token"])
    txt(tok[-48:] if tok else "Ctrl+V — вставить ключ", F, FG if tok else DIM, (372, 28))
    rr(EYE_RECT, PANEL)
    txt("скрыть" if S["show"] else "показать", FS, FG, EYE_RECT.center, center=True)
    gc = GREEN if S["giga_state"] == "готов" else YELLOW
    cc = GREEN if S["cmd_state"] == "загружены" else YELLOW
    txt(f"GigaAM: {S['giga_state']}", FXS, gc, (985, 18))
    txt(f"Команды: {S['cmd_state']}", FXS, cc, (985, 40))
    for rect, key, label in ((TAB_TEST, "test", "Тест команд"), (TAB_FREE, "free", "Свободная речь")):
        on = S["tab"] == key
        rr(rect, PANEL2 if on else BG, 8)
        txt(label, FB, FG if on else DIM, rect.center, center=True)
    pygame.draw.line(screen, LINE, (20, 128), (W - 20, 128))


def draw_level(y):
    rr(pygame.Rect(400, y, 740, 12), PANEL, 6)
    w = int(740 * min(1.0, S["level"] / 5000))
    col = RED if S["phase"] == "speech" else BLUE
    if w > 4:
        rr(pygame.Rect(400, y, w, 12), col, 6)
    label = {"listen": "жду голос", "speech": "слышу тебя", "recog": "распознаю", "show": "", "idle": ""}[S["phase"]]
    if label:
        txt(label, FXS, col if S["phase"] != "recog" else YELLOW, (400, y + 16))


def draw_test():
    # список фраз
    rr(LIST_RECT, PANEL)
    old = screen.get_clip()
    screen.set_clip(LIST_RECT.inflate(-4, -4))
    row_h = 38
    target = max(0, S["idx"] * row_h - LIST_RECT.h // 2)
    if S["running"]:
        S["list_scroll"] = target
    S["list_scroll"] = max(0, min(S["list_scroll"], len(PHRASES) * row_h - LIST_RECT.h + 10))
    for i, (p, _) in enumerate(PHRASES):
        y = LIST_RECT.y + 6 + i * row_h - S["list_scroll"]
        if y < LIST_RECT.y - row_h or y > LIST_RECT.bottom:
            continue
        if i == S["idx"]:
            rr(pygame.Rect(LIST_RECT.x + 6, y, LIST_RECT.w - 12, row_h - 4), PANEL2, 8)
        txt(f"{i + 1}", FXS, DIM, (LIST_RECT.x + 14, y + 8))
        txt(p[:28], FS, FG if i == S["idx"] else DIM, (LIST_RECT.x + 44, y + 7))
        for k, eng in enumerate(("giga", "aqua")):
            v = verdict(i, eng)
            col = LINE if v is None else (GREEN if v else RED)
            if S["results"].get(i, {}).get("silent"):
                col = YELLOW
            pygame.draw.circle(screen, col, (LIST_RECT.right - 50 + k * 24, y + 15), 7)
    screen.set_clip(old)
    ly = LIST_RECT.y - 16
    pygame.draw.circle(screen, GREEN, (LIST_RECT.right - 50, ly + 8), 5)
    pygame.draw.circle(screen, BLUE, (LIST_RECT.right - 26, ly + 8), 5)
    txt("Giga / Aqua:  ", FXS, DIM, (LIST_RECT.right - 130, ly))

    done = S["idx"] >= len(PHRASES)
    i = min(S["idx"], len(PHRASES) - 1)
    phrase, exp = PHRASES[i]
    if done:
        txt("Тест окончен", FH, GREEN, (400, 140))
    else:
        for k, l in enumerate(wrap("«" + phrase + "»", FH, 740)[:2]):
            txt(l, FH, FG, (400, 138 + k * 48))
        txt(f"фраза {i + 1} из {len(PHRASES)}   ·   ожидается команда: {exp}", FS, DIM, (400, 232))
    draw_level(262)
    txt(S["msg"], FS, DIM, (400, 296))

    res = S["results"].get(i if not done else len(PHRASES) - 1) or {}
    exp_name = None if done else exp
    result_card(pygame.Rect(400, 326, 362, 190), "GigaAM · офлайн", GREEN, res.get("giga"), exp_name)
    result_card(pygame.Rect(778, 326, 362, 190), "Aqua Voice · Avalon", BLUE, res.get("aqua"), exp_name)

    # итоги
    rr(pygame.Rect(400, 528, 740, 70), PANEL)
    for k, (eng, name, col) in enumerate((("giga", "GigaAM", GREEN), ("aqua", "Aqua", BLUE))):
        ok, tot, ms = score(eng)
        x = 420 + k * 370
        pct = f"{ok * 100 // tot}%" if tot else "—"
        txt(f"{name}: {ok}/{tot}  ({pct})", FB, col, (x, 538))
        txt(f"средний ответ: {ms} мс" if tot else "средний ответ: —", FS, DIM, (x, 568))

    button(BTN_START, "Пауза" if S["running"] else ("Старт" if S["idx"] < len(PHRASES) else "Заново"),
           RED if S["running"] else GREEN)
    button(BTN_SKIP, "Пропуск", VIOLET, S["running"])
    button(BTN_RESET, "Сначала", PANEL2)
    txt("Пробел — старт / пауза   ·   колесо мыши — прокрутка списка", FXS, DIM, (400, 678))


def draw_free():
    txt("Говори любую фразу: увидишь текст обоих движков и какая команда Кеши сработает.", FS, DIM, (20, 144))
    draw_level(190)
    txt(S["msg"] if S["msg"] != "Нажми «Старт» и читай фразы вслух." else "Нажми «Записать» и говори.",
        FS, DIM, (20, 214))
    fr = S["free"] or {}
    result_card(pygame.Rect(20, 250, 550, 300), "GigaAM · офлайн", GREEN, fr.get("giga"))
    result_card(pygame.Rect(590, 250, 550, 300), "Aqua Voice · Avalon", BLUE, fr.get("aqua"))
    BTN_FREE.topleft = (20, 580)
    button(BTN_FREE, "Записать" if not S["running"] else "слушаю…", RED if not S["running"] else PANEL2,
           not S["running"])
    txt("Запись останавливается сама после паузы в речи.", FXS, DIM, (340, 598))


def toggle_run():
    if S["running"]:
        S["abort"] = True
        S["running"] = False
        return
    if S["idx"] >= len(PHRASES):
        S["idx"], S["results"] = 0, {}
    spawn(test_loop)


def reset():
    S["abort"] = True
    S["running"] = False
    time.sleep(0.15)
    S["idx"], S["results"], S["msg"] = 0, {}, "Нажми «Старт» и читай фразы вслух."


def on_click(pos):
    S["focus"] = TOKEN_RECT.collidepoint(pos)
    if EYE_RECT.collidepoint(pos):
        S["show"] = not S["show"]
    if TAB_TEST.collidepoint(pos) and not S["running"]:
        S["tab"] = "test"
    if TAB_FREE.collidepoint(pos) and not S["running"]:
        S["tab"], S["msg"] = "free", "Нажми «Записать» и говори."
    if S["tab"] == "test":
        if BTN_START.collidepoint(pos):
            toggle_run()
        elif BTN_SKIP.collidepoint(pos) and S["running"]:
            S["skip"] = True
        elif BTN_RESET.collidepoint(pos):
            reset()
    elif BTN_FREE.collidepoint(pos):
        spawn(free_once)


def paste():
    try:
        import tkinter
        r = tkinter.Tk()
        r.withdraw()
        t = r.clipboard_get()
        r.destroy()
        return t.strip()
    except Exception:
        return ""


load_backend()
clock = pygame.time.Clock()
while True:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            S["abort"] = True
            pygame.quit()
            sys.exit()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            on_click(e.pos)
        if e.type == pygame.MOUSEWHEEL and S["tab"] == "test" and not S["running"]:
            S["list_scroll"] -= e.y * 40
        if e.type == pygame.KEYDOWN:
            ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL
            if S["focus"]:
                if e.key == pygame.K_v and ctrl:
                    S["token"] = paste()
                elif e.key == pygame.K_a and ctrl:
                    S["token"] = ""
                elif e.key == pygame.K_BACKSPACE:
                    S["token"] = S["token"][:-1]
            elif e.key == pygame.K_SPACE and S["tab"] == "test":
                toggle_run()
        if e.type == pygame.TEXTINPUT and S["focus"]:
            S["token"] += e.text

    screen.fill(BG)
    draw_header()
    draw_test() if S["tab"] == "test" else draw_free()
    pygame.display.flip()
    clock.tick(30)
