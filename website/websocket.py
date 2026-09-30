from fastapi import WebSocket


class WSManager:
    def __init__(self):
        self.clients = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, data):
        dead = []
        for c in self.clients:
            try:
                await c.send_json(data)
            except Exception:
                dead.append(c)
        for d in dead:
            self.disconnect(d)


ws_manager = WSManager()
