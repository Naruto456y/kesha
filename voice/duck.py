"""
Приглушение фона, как у Алисы: услышала «Кеша» — музыка, браузер, видео стихают до DUCK_LEVEL,
пока Кеша слушает и отвечает, потом громкость возвращается.

Глушим не общую громкость, а каждое приложение в микшере Windows (pycaw), кроме самой Кеши:
иначе её ответ тоже звучал бы на 20%. Общую громкость и команды «громче/тише» не трогаем.
"""
import atexit
import os
import threading

from config import DUCK_LEVEL

_lock = threading.Lock()
_saved = {}            # pid -> громкость до приглушения


def _sessions():
    import comtypes
    from pycaw.pycaw import AudioUtilities
    comtypes.CoInitialize()          # голосовой цикл — не главный поток
    me = os.getpid()
    return [s for s in AudioUtilities.GetAllSessions() if s.ProcessId not in (0, me)]


def duck(level=None):
    """Приглушить всё, кроме Кеши. Повторный вызов ничего не портит: громкость «до» помним с первого."""
    level = DUCK_LEVEL if level is None else level
    if not level or level >= 1:
        return
    with _lock:
        try:
            for s in _sessions():
                vol = s.SimpleAudioVolume
                now = vol.GetMasterVolume()
                if s.ProcessId not in _saved:
                    _saved[s.ProcessId] = now
                if now > level:
                    vol.SetMasterVolume(level, None)
        except Exception as e:
            print(f"[duck] не смог приглушить: {e}")


def restore():
    """Вернуть громкость приложениям, которые приглушили."""
    with _lock:
        if not _saved:
            return
        try:
            for s in _sessions():
                before = _saved.get(s.ProcessId)
                if before is not None:
                    s.SimpleAudioVolume.SetMasterVolume(before, None)
        except Exception as e:
            print(f"[duck] не смог вернуть громкость: {e}")
        finally:
            _saved.clear()


def is_ducked():
    return bool(_saved)


atexit.register(restore)     # Кешу закрыли посреди фразы — музыка не должна остаться тихой
