"""help_manager (пакет pycraft-tools) при импорте делает `import vlc`.
python-vlc на Windows без установленного VLC падает (libvlc.dll не найден),
и вместе с ним отваливается весь help_manager — а с ним GigaChat.
VLC нужен help_manager только для музыкального плеера Music, поэтому
без VLC подставляем пустой модуль: GigaChat работает, плеер — нет.
Импортировать этот модуль до `from help_manager import ...`."""
import sys
import types

VLC_AVAILABLE = True
try:
    import vlc  # noqa: F401
except Exception as e:  # OSError: libvlc.dll не найден / ImportError: нет python-vlc
    VLC_AVAILABLE = False
    sys.modules["vlc"] = types.ModuleType("vlc")
    print(f"[help_manager] VLC не найден ({e.__class__.__name__}) — плеер Music выключен, "
          "остальное работает. Нужен плеер — поставьте VLC 64-bit: https://www.videolan.org/")
