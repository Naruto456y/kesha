"""
Kesha bootloader.
Этот файл собирается в Kesha.exe.
При запуске он ищет свежий main.py в папке проекта и запускает его
в ТОМ ЖЕ процессе. Правки .py подхватываются без пересборки .exe.
"""
import os
import sys
import runpy
import ctypes

# --- AUMID: чтобы Windows показывала иконку Kesha, а не питон ---
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "Yusuf.Kesha.VoiceAssistant.1.0"
    )
except Exception:
    pass

# --- Определяем папку, откуда запущен .exe ---
if getattr(sys, "frozen", False):
    # Запущено как собранный .exe
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
else:
    # Запущено как .py
    exe_dir = os.path.dirname(os.path.abspath(__file__))

# --- Ищем main.py в нескольких местах ---
candidates = [
    os.path.join(exe_dir, "main.py"),                                      # рядом с .exe
    os.path.join(exe_dir, "kesha", "main.py"),                             # в подпапке
    os.environ.get("KESHA_PROJECT_DIR", ""),                               # через переменную
    r"C:\Users\Yusuf\Programming\Python\projects\kesha\main.py",            # жёсткий путь (fallback)
]

project_main = None
project_dir = None

for c in candidates:
    if c and os.path.isfile(c):
        project_main = c
        project_dir = os.path.dirname(c)
        break

if not project_main:
    msg = (
        "main.py не найден рядом с Kesha.exe.\n\n"
        f"Проверенные пути:\n" + "\n".join(f"  - {c}" for c in candidates if c)
    )
    try:
        ctypes.windll.user32.MessageBoxW(0, msg, "Kesha — ошибка", 0x10)
    except Exception:
        print(msg, file=sys.stderr)
    sys.exit(1)

# --- Рабочая папка = папка проекта ---
os.chdir(project_dir)

# --- Добавляем папку проекта в начало sys.path ---
# Это гарантирует, что команды (commands.py, core.py, voice/ и т.д.)
# импортируются из СВЕЖИХ .py файлов, а не из временной распаковки.
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# --- Запускаем main.py как скрипт, в текущем процессе ---
runpy.run_path(project_main, run_name="__main__")