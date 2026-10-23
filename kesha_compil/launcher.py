"""
Kesha launcher — тонкая обёртка, которая запускает main.py
из папки проекта в фоне без консоли.

Этот .py вшивается в Kesha.exe. Сам main.py и все модули
Кеши НЕ вшиты — они берутся из папки проекта при каждом запуске.
Так правки в .py подхватываются без пересборки .exe.
"""
import os
import sys
import subprocess
import ctypes

# ---------- AUMID — чтобы иконка в панели задач не путалась с Python ----------
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "Yusuf.Kesha.VoiceAssistant.1.0"
    )
except Exception:
    pass

# ---------- Путь к папке с Kesha.exe ----------
# sys.argv[0] = путь к .exe (или к .py, если запущен из исходника)
exe_path = os.path.abspath(sys.argv[0])
exe_dir = os.path.dirname(exe_path)

# ---------- Ищем main.py в папке проекта ----------
# Вариант 1: main.py лежит рядом с .exe
main_py = os.path.join(exe_dir, "main.py")

# Вариант 2: main.py в подпапке kesha
if not os.path.exists(main_py):
    main_py = os.path.join(exe_dir, "kesha", "main.py")

# Вариант 3: жёсткий путь (если .exe на рабочем столе, а проект в другом месте)
if not os.path.exists(main_py):
    hardcoded = r"C:\Users\Yusuf\Programming\Python\kesha\main.py"
    if os.path.exists(hardcoded):
        main_py = hardcoded

if not os.path.exists(main_py):
    ctypes.windll.user32.MessageBoxW(
        0,
        "main.py не найден.\n\nПоложите Kesha.exe в папку проекта Кеши\n"
        "или убедитесь, что проект лежит по пути:\n"
        r"C:\Users\Yusuf\Programming\Python\kesha",
        "Kesha — ошибка",
        0x10,  # MB_ICONERROR
    )
    sys.exit(1)

# ---------- Ищем pythonw.exe ----------
# Вариант 1: рядом с .exe
pythonw = os.path.join(exe_dir, "pythonw.exe")

# Вариант 2: системный PATH
if not os.path.exists(pythonw):
    import shutil
    pythonw = shutil.which("pythonw") or shutil.which("pythonw.exe")

# Вариант 3: стандартный путь Python 3.13
if not pythonw or not os.path.exists(pythonw):
    candidates = [
        r"C:\Users\Yusuf\AppData\Local\Programs\Python\Python313\pythonw.exe",
        r"C:\Python313\pythonw.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            pythonw = c
            break

if not pythonw or not os.path.exists(pythonw):
    ctypes.windll.user32.MessageBoxW(
        0,
        "pythonw.exe не найден.\n\nУстановите Python 3.13 или добавьте его в PATH.",
        "Kesha — ошибка",
        0x10,
    )
    sys.exit(1)

# ---------- Запуск main.py через pythonw (без консоли, в фоне) ----------
project_dir = os.path.dirname(main_py)

# Флаги для отвязки от родителя — чтобы .exe можно было закрыть
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000

try:
    subprocess.Popen(
        [pythonw, main_py],
        cwd=project_dir,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
        close_fds=True,
    )
except Exception as e:
    ctypes.windll.user32.MessageBoxW(
        0,
        f"Не удалось запустить Кешу:\n\n{e}",
        "Kesha — ошибка",
        0x10,
    )
    sys.exit(1)

# Лаунчер завершается сразу — main.py продолжает работать отдельно.
sys.exit(0)