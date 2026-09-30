from fastapi import HTTPException, Request
from config import WEB_PASSWORD


def check_password(request: Request) -> bool:
    if request.headers.get("X-Password") != WEB_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong password")
    return True
