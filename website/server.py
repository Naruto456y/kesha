"""FastAPI веб-сервер Кеши."""
import asyncio
import re
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from core import handle_command, subscribe
from state_manager import register_ws_emitter, snapshot
from config import WEB_HOST, WEB_PORT, UPLOAD_DIR, BASE_DIR
from .auth import COOKIE_NAME, check_media, check_password, new_session, password_ok
from .streaming import generate_frames
from .websocket import ws_manager

FE = BASE_DIR / "website" / "frontend"
app = FastAPI(title="Kesha Web")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

if FE.exists():
    app.mount("/static", StaticFiles(directory=str(FE)), name="static")
UPLOAD_DIR.mkdir(exist_ok=True)
_UPLOAD_ROOT = UPLOAD_DIR.resolve()
_SHOT_RE = re.compile(r"/uploads/[\w.\-]+\.png")


_ws_loop = None


@app.on_event("startup")
async def _on_startup():
    global _ws_loop
    _ws_loop = asyncio.get_running_loop()
    # смены состояния голоса (IDLE/LISTENING/...) -> во все WebSocket-клиенты
    register_ws_emitter(ws_manager.broadcast, loop=_ws_loop)


def _on_core(source, text, response):
    if _ws_loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast({"type": "message", "source": source,
                                  "text": text, "response": response}),
            _ws_loop,
        )
    except Exception as e:
        print("[ws]", e)


subscribe(_on_core)


@app.get("/", response_class=HTMLResponse)
async def login_page():
    f = FE / "login.html"
    return f.read_text(encoding="utf-8") if f.exists() else "login missing"


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    f = FE / "chat.html"
    return f.read_text(encoding="utf-8") if f.exists() else "chat missing"


@app.post("/login")
async def login(request: Request):
    data = await request.json()
    ok = password_ok(data.get("password"))
    resp = JSONResponse({"success": ok}, status_code=200 if ok else 401)
    if ok:
        resp.set_cookie(COOKIE_NAME, new_session(), httponly=True, samesite="lax")
    return resp


@app.get("/api/commands")
async def api_commands(request: Request):
    check_password(request)
    from core import registry
    return {"commands": [
        {"patterns": c["patterns"], "description": c["description"], "category": c["category"]}
        for c in registry.commands
    ]}


@app.post("/api/command")
async def api_command(request: Request):
    check_password(request)
    data = await request.json()
    text = data.get("command", "")
    result = await asyncio.to_thread(handle_command, text, "website")
    shot = _SHOT_RE.search(result or "")
    return {"result": result, "image_url": shot.group(0) if shot else None}


@app.post("/api/upload")
async def api_upload(request: Request, file: UploadFile = File(...)):
    check_password(request)
    # только имя файла: «../» и абсолютные пути отбрасываются; префикс исключает перезапись чужих файлов
    safe = re.sub(r"[^\w.\-]", "_", Path(file.filename or "").name) or "file"
    name = f"{secrets.token_hex(4)}_{safe}"
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Файл больше 50 МБ")
    (_UPLOAD_ROOT / name).write_bytes(data)
    return {"file_url": "/uploads/" + name}


@app.get("/uploads/{name}")
async def get_upload(name: str, request: Request):
    check_media(request)
    path = (_UPLOAD_ROOT / name).resolve()
    if path.parent != _UPLOAD_ROOT or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/stream")
async def stream(request: Request):
    check_media(request)
    return StreamingResponse(generate_frames(),
                             media_type="multipart/x-mixed-replace; boundary=frame")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    try:
        check_media(ws)
    except HTTPException:
        await ws.close(code=1008)
        return
    await ws_manager.connect(ws)
    try:
        await ws.send_json(snapshot())
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(ws)


def start_website():
    print("[web] http://%s:%s" % (WEB_HOST, WEB_PORT))
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT, log_level="info")


if __name__ == "__main__":
    start_website()
