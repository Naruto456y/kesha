# Хук Claude Code: после правки файла проекта перезапускает Кешу.
$raw = [Console]::In.ReadToEnd()
try { $p = ($raw | ConvertFrom-Json).tool_input.file_path } catch { $p = "" }
$root = "C:\Users\Yusuf\Programming\Python\projects\kesha"
if (-not $p -or -not $p.Replace("/", "\").StartsWith($root, "OrdinalIgnoreCase")) { exit 0 }
if ($p -match "\\(tests|docs|\.claude)\\|\.md$|\.txt$") { exit 0 }

Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -match "kesha\\main\.py" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 800
Start-Process "C:\Users\Yusuf\AppData\Local\Programs\Python\Python313\pythonw.exe" `
    -ArgumentList "`"$root\main.py`"" -WorkingDirectory $root
exit 0
