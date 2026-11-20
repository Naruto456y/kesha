@echo off
chcp 65001 >nul
rem Собрать Kesha.exe (один раз; после правок .py пересобирать не нужно).
rem Компилятор C# встроен в Windows (.NET Framework 4), ничего качать не надо.
cd /d "%~dp0.."
"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /optimize ^
  /win32icon:Media\Kesha.ico /out:Kesha.exe /reference:System.Windows.Forms.dll launcher\Kesha.cs
if errorlevel 1 exit /b 1
echo Готово: %CD%\Kesha.exe
