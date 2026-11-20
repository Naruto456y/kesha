"""Сайт «Студия дизайна»: маленький локальный сервер (только 127.0.0.1) для редакторов
интерфейса и реактора. Открывается в обычном браузере, настройки сохраняет в settings."""
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import settings

PORT = 8765
UI_DIR = Path(__file__).parent / "ui"
EDITABLE = ("design", "reactor")          # что разрешено менять через сайт
_server = None


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _host_ok(self):
        return self.headers.get("Host", "") in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, "{}")
        path = urlparse(self.path).path
        if path == "/api/settings":
            return self._send(200, json.dumps({k: settings.get(k) for k in EDITABLE}, ensure_ascii=False))
        rel = "studio.html" if path in ("/", "") else path.lstrip("/")
        f = (UI_DIR / rel).resolve()
        if UI_DIR.resolve() not in f.parents or not f.is_file():
            return self._send(404, "not found", "text/plain")
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        self._send(200, f.read_bytes(), ctype)

    def do_POST(self):
        origin = self.headers.get("Origin")
        if (not self._host_ok() or urlparse(self.path).path != "/api/set"
                or (origin and origin not in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"))
                or "application/json" not in self.headers.get("Content-Type", "")):
            return self._send(403, "{}")
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 200_000:
                raise ValueError("слишком большой запрос")
            body = json.loads(self.rfile.read(n))
            key, value = body["key"], body["value"]
            if key not in EDITABLE:
                raise ValueError("ключ не разрешён")
            settings.set(key, value)
            self._send(200, '{"ok":true}')
        except Exception as e:
            self._send(400, json.dumps({"error": str(e)}, ensure_ascii=False))


def start():
    """Запустить сервер (один раз). Возвращает URL сайта."""
    global _server
    if _server is None:
        try:
            _server = ThreadingHTTPServer(("127.0.0.1", PORT), _Handler)
        except OSError as e:
            print("[studio] порт занят:", e)
            return None
        threading.Thread(target=_server.serve_forever, daemon=True, name="studio").start()
    return f"http://127.0.0.1:{PORT}/"


def open_in_browser(tab=""):
    import webbrowser
    url = start()
    if url:
        webbrowser.open(url + (f"#{tab}" if tab else ""))
    return url
