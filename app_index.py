"""
Поиск программ по ярлыкам меню «Пуск» и рабочего стола.

AppOpener видит не всё (Obsidian, CapCut, Dota 2 у него нет), а GigaAM пишет
латинские названия как слышит: «обсидиан», «psidion», «bsidin». Здесь:
  - индекс ярлыков .lnk/.url (без деинсталляторов и справки);
  - русские названия и частые искажения -> настоящее имя (ALIASES);
  - транслит + нечёткое сравнение, но только с высоким порогом.

    find("обсидиан") -> ("obsidian", r"...\\Obsidian.lnk")
"""
import difflib
import json
import os
import re
import subprocess
import threading
from pathlib import Path

from config import DATA_DIR

APPS_JSON = DATA_DIR / "apps.json"      # имя -> настоящий .exe (tools/build_app_db.py)

ALIASES = {
    "obsidian": ["обсидиан", "обсидиан", "абсидиан", "обсидиана", "psidion", "bsidin", "epident",
                 "obsidion", "absidian", "обсидион", "псидион"],
    "telegram": ["телеграм", "телеграмм", "телега", "телегу", "тг", "телеграмма"],
    "steam": ["стим", "стим", "стима"],
    "dota 2": ["дота", "доту", "дота 2", "доту 2", "дотку"],
    "blender 4.2": ["блендер", "блендр"],
    "capcut": ["капкат", "кап кат", "капкут", "кэпкат"],
    "google chrome": ["хром", "гугл хром", "гугл", "chrome"],
    "браузер opera gx": ["опера", "оперу", "опера gx", "оперу gx", "opera"],
    "zoom workplace": ["зум", "zoom"],
    "unity hub": ["юнити", "unity"],
    "gimp 3.0.4": ["гимп", "gimp"],
    "vlc media player": ["влс", "vlc", "влц", "видеоплеер"],
    "word": ["ворд", "word"],
    "excel": ["эксель", "ексель", "excel"],
    "powerpoint": ["повер поинт", "поверпоинт", "пауэрпоинт", "презентации", "powerpoint"],
    "paint": ["паинт", "пэинт", "пейнт", "рисовалку"],
    "tlauncher": ["тлаунчер", "ти лаунчер", "т лаунчер"],
    "мовавика видео 25": ["мовавика", "мовавику", "movavi"],
    "github desktop": ["гитхаб", "гит хаб", "github"],
    "claude": ["клод", "клоуд", "клауд", "claude", "cloud", "kloyd", "kloud", "клауде", "клода"],
    "ollama": ["оллама", "олама", "ollama"],
    "everything": ["эвризинг", "эверифинг", "поиск файлов"],
    "voicemod": ["войсмод", "voicemod", "изменитель голоса"],
    "ccleaner 7": ["сиклинер", "клинер", "ccleaner"],
    "logitech g hub": ["джи хаб", "g hub", "логитек"],
    "яндекс музыка": ["яндекс музыку", "яндекс музыка"],
    "bluestacks store": ["блюстакс", "bluestacks"],
    "ldplayer 9": ["лд плеер", "ldplayer", "эмулятор"],
    "freecad 1.1": ["фрикад", "freecad"],
    "bambu studio": ["бамбу", "бамбу студио", "bambu"],
    "photopea": ["фотопеа", "фотопия"],
    "picsart - photo studio": ["пиксарт", "picsart"],
    "speedify": ["спидифай", "speedify"],
    "hiddify": ["хиддифай", "хидифай", "hiddify"],
    "radmin vpn": ["радмин", "радмин впн"],
    "sticky notes (new)": ["стикеры", "заметки на экране"],
    "мэш": ["мэш", "мош", "электронный дневник"],
    "часы": ["часы", "будильники windows"],
    "фотографии": ["фотографии", "фотки", "галерею"],
}

_SKIP = re.compile(r"uninstall|удалить|деинсталл|readme|documentation|dokumentation|website|wiki|faq|"
                   r"release notes|license|help|support|сайт|очистить|настройки запуска|"
                   r"\(2\)$|reset preferences|generat|генерировать|журнала|^kesha|кеша", re.I)

_TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
               ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "i", "k", "l", "m", "n", "o", "p", "r",
                "s", "t", "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))

_cache = None
_db = None
_lock = threading.Lock()


def is_junk(name: str) -> bool:
    return bool(_SKIP.search(name))


def app_db(refresh=False) -> dict:
    """data/apps.json: {имя: {"path": .exe, "args", "cwd", "shortcut"}}. Нет файла — собрать один раз."""
    global _db
    if _db is not None and not refresh:
        return _db
    try:
        if refresh or not APPS_JSON.exists():
            from tools.build_app_db import build
            _db = build()
        else:
            _db = json.loads(APPS_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[app_index] база приложений: {e}")
        _db = {}
    return _db


def launch(path: str):
    """.exe из базы — напрямую, с аргументами и рабочей папкой ярлыка; остальное — os.startfile."""
    e = next((e for e in app_db().values() if e.get("path") == path), None)
    if not path.lower().endswith(".exe") or not os.path.exists(path):
        os.startfile(path)
        return
    cwd = (e or {}).get("cwd") or os.path.dirname(path)
    args = (e or {}).get("args") or ""
    subprocess.Popen(f'"{path}" {args}'.strip(), cwd=cwd if os.path.isdir(cwd) else None, close_fds=True,
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)


def translit(s: str) -> str:
    return "".join(_TR.get(c, c) for c in s.lower())


def _dirs():
    env = os.environ
    return [Path(env.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(env.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(env.get("USERPROFILE", "")) / "Desktop"]


def shortcuts(refresh=False) -> dict:
    """{«имя ярлыка в нижнем регистре»: путь}; из базы apps.json — сразу путь к .exe."""
    global _cache
    with _lock:
        if _cache is not None and not refresh:
            return _cache
        found = {}
        for d in _dirs():
            if not d.is_dir():
                continue
            for p in list(d.rglob("*.lnk")) + list(d.rglob("*.url")):
                name = p.stem.lower().strip()
                if name and not _SKIP.search(name) and name not in found:
                    found[name] = str(p)
        found.update({n: e["path"] for n, e in app_db(refresh).items() if e.get("path")})
        _cache = found
        return found


def _clean(q: str) -> str:
    q = q.lower().replace("ё", "е")
    q = re.sub(r"\b(?:мне|пожалуйста|программу|приложение|игру|ка)\b", " ", q)
    return " ".join(q.split())


def find(query: str, index: dict = None, cutoff: float = 0.75):
    """-> (имя, путь) или None. Только уверенные совпадения: открыть не то хуже, чем переспросить."""
    index = shortcuts() if index is None else index
    q = _clean(query)
    if not q:
        return None
    for name, words in ALIASES.items():            # «открой обсидиан», «запусти доту»
        if any(q == w or re.search(rf"(?<!\w){re.escape(w)}(?!\w)", q) for w in words):
            if name in index:
                return name, index[name]
    if q in index:
        return q, index[q]
    names = list(index)
    for cand in (q, translit(q)):
        starts = [n for n in names if n.startswith(cand + " ") or n == cand]
        if starts:
            n = min(starts, key=len)
            return n, index[n]
        m = difflib.get_close_matches(cand, names, n=1, cutoff=cutoff)
        if m:
            return m[0], index[m[0]]
    return None
