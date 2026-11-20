"""
Ярлыки «Кеша» → Kesha.exe с логотипом и тем же AppUserModelID, что ставит main.py:
  • Пуск      — отсюда «Закрепить на панели задач» (окно и значок сольются в одну кнопку);
  • Рабочий стол;
  • Автозагрузка — Kesha.exe --minimized (окно стартует свёрнутым).

    python tools/install_shortcuts.py            # создать / обновить
    python tools/install_shortcuts.py --remove   # убрать (и из автозагрузки)
"""

import os
import re
import sys
from pathlib import Path

import pythoncom
from win32com.propsys import propsys, pscon
from win32com.shell import shell, shellcon

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "Kesha.exe"
ICON = ROOT / "Media" / "Kesha.ico"
NAME = "Кеша.lnk"
APP_ID = re.search(r'APP_ID = "([^"]+)"', (ROOT / "main.py").read_text(encoding="utf-8")).group(1)


def folders() -> dict:
    get = lambda csidl: Path(shell.SHGetFolderPath(0, csidl, 0, 0))   # учитывает перенос в OneDrive
    return {
        "Пуск": get(shellcon.CSIDL_PROGRAMS),
        "Рабочий стол": get(shellcon.CSIDL_DESKTOPDIRECTORY),
        "Автозагрузка": get(shellcon.CSIDL_STARTUP),
    }


def make(path: Path, args: str = ""):
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None,
                                      pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    link.SetPath(str(EXE))
    link.SetArguments(args)
    link.SetWorkingDirectory(str(ROOT))
    link.SetIconLocation(str(ICON), 0)
    link.SetDescription("Голосовой помощник Кеша")
    store = link.QueryInterface(propsys.IID_IPropertyStore)
    store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(APP_ID))
    store.Commit()
    link.QueryInterface(pythoncom.IID_IPersistFile).Save(str(path), 0)


def main():
    remove = "--remove" in sys.argv
    if not remove and not EXE.exists():
        sys.exit(f"Нет {EXE} — сначала собери: launcher\\build.bat")
    for title, folder in folders().items():
        path = folder / NAME
        if remove:
            if path.exists():
                path.unlink()
                print(f"Убрал: {title} ({path})")
            continue
        make(path, "--minimized" if title == "Автозагрузка" else "")
        print(f"Готово: {title} ({path})")


if __name__ == "__main__":
    main()
