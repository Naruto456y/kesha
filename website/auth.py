import hmac
import secrets

from fastapi import HTTPException
from starlette.requests import HTTPConnection

from config import WEB_PASSWORD

COOKIE_NAME = "kesha_auth"
_sessions = set()


def password_ok(value) -> bool:
    """Сравнение пароля за постоянное время. Пустой WEB_PASSWORD — доступ закрыт всем."""
    if not WEB_PASSWORD or not isinstance(value, str):
        return False
    return hmac.compare_digest(value.encode("utf-8"), WEB_PASSWORD.encode("utf-8"))


def new_session() -> str:
    token = secrets.token_urlsafe(32)
    _sessions.add(token)
    return token


def check_password(request: HTTPConnection) -> bool:
    """Для API: пароль в заголовке X-Password."""
    if not password_ok(request.headers.get("X-Password")):
        raise HTTPException(status_code=401, detail="Wrong password")
    return True


def check_media(request: HTTPConnection) -> bool:
    """Для <img>/WebSocket, где заголовок не поставить: кука сессии (выдаётся в /login) или X-Password."""
    if request.cookies.get(COOKIE_NAME) in _sessions or password_ok(request.headers.get("X-Password")):
        return True
    raise HTTPException(status_code=401, detail="Unauthorized")
