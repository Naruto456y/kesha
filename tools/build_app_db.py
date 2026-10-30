"""
База приложений для «открой X»: ярлыки рабочего стола (свой и общий) и меню «Пуск»
-> настоящие .exe, на которые они ссылаются. Результат: data/apps.json.

    python tools/build_app_db.py

Кеша читает data/apps.json при «открой ...» (app_index.find); если файла нет — собирает сам.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DATA_DIR  # noqa: E402

APPS_JSON = DATA_DIR / "apps.json"

# PowerShell: WScript.Shell раскрывает .lnk в цель, аргументы и рабочую папку
_PS = r"""
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$sh = New-Object -ComObject WScript.Shell
# рабочие столы — только верхний уровень (там папки проектов), «Пуск» — с подпапками
$dirs = @(@([Environment]::GetFolderPath('Desktop'), $false), @([Environment]::GetFolderPath('CommonDesktopDirectory'), $false),
          @([Environment]::GetFolderPath('Programs'), $true), @([Environment]::GetFolderPath('CommonPrograms'), $true))
$out = foreach ($p in $dirs) {
  $d = $p[0]
  if (-not $d -or -not (Test-Path -LiteralPath $d)) { continue }
  Get-ChildItem -LiteralPath $d -File -Recurse:$p[1] -ErrorAction SilentlyContinue |
    Where-Object { '.lnk', '.url', '.exe' -contains $_.Extension.ToLower() } | ForEach-Object {
    $t = ''; $a = ''; $w = ''
    if ($_.Extension -eq '.lnk') { $l = $sh.CreateShortcut($_.FullName); $t = $l.TargetPath; $a = $l.Arguments; $w = $l.WorkingDirectory }
    [pscustomobject]@{ name = $_.BaseName; file = $_.FullName; target = $t; args = $a; cwd = $w; desktop = -not $p[1] }
  }
}
$out | ConvertTo-Json -Compress
"""


def scan():
    raw = subprocess.run(["powershell", "-NoProfile", "-Command", _PS], capture_output=True,
                         timeout=120, encoding="utf-8", errors="replace").stdout.strip()
    items = json.loads(raw) if raw else []
    return items if isinstance(items, list) else [items]


def build(items=None):
    """-> {имя в нижнем регистре: {"path", "args", "cwd", "shortcut"}}. Рабочий стол важнее «Пуска»."""
    import app_index
    db = {}
    for it in sorted(items if items is not None else scan(), key=lambda i: not i.get("desktop")):
        name = (it.get("name") or "").lower().strip()
        if not name or app_index.is_junk(name) or name in db:
            continue
        target = it.get("target") or ""
        exe = target if target.lower().endswith(".exe") and Path(target).exists() else ""
        db[name] = {"path": exe or it["file"], "args": it.get("args") or "",
                    "cwd": it.get("cwd") or "", "shortcut": it["file"]}
    APPS_JSON.parent.mkdir(parents=True, exist_ok=True)
    APPS_JSON.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
    return db


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    db = build()
    exe = sum(v["path"].lower().endswith(".exe") for v in db.values())
    print(f"✅ {len(db)} приложений, из них {exe} с прямым путём к .exe -> {APPS_JSON}")
