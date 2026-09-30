"""FastAPI веб-сервер Кеши."""
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core import handle_command, subscribe
from config import WEB_HOST, WEB_PORT, WEB_PASSWORD, UPLOAD_DIR, BASE_DIR
from .auth import check_password
from .streaming import generate_frames
from .websocket import ws_manager

FE = BASE_DIR / "website" / "frontend"
app = FastAPI(title="Kesha Web")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"], allow_credentials=True)

if FE.exists():
    app.mount("/static", StaticFiles(directory=str(FE)), name="static")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


_ws_loop = None


@app.on_event("startup")
async def _on_startup():
    global _ws_loop
    _ws_loop = asyncio.get_running_loop()


def _on_core(source, text, response):
    if _ws_loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast({"source": source, "text": text, "response": response}),
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
    ok = data.get("password") == WEB_PASSWORD
    return JSONResponse({"success": ok}, status_code=200 if ok else 401)


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
    return {"result": result, "image_url": None}


@app.post("/api/upload")
async def api_upload(request: Request, file: UploadFile = File(...)):
    check_password(request)
    path = UPLOAD_DIR / file.filename
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"file_url": "/uploads/" + file.filename}


@app.get("/stream")
async def stream(request: Request, password: str = None):
    if password != WEB_PASSWORD and request.headers.get("X-Password") != WEB_PASSWORD:
        raise HTTPException(401)
    return StreamingResponse(generate_frames(),
                             media_type="multipart/x-mixed-replace; boundary=frame")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


def start_website():
    print("[web] http://%s:%s" % (WEB_HOST, WEB_PORT))
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT, log_level="info")


if __name__ == "__main__":
    start_website()
