import subprocess
import shutil
"""Навык Алисы - Flask."""
from flask import Flask, request, jsonify
from core import handle_command
from config import ALICE_HOST, ALICE_PORT, ALICE_ALLOWED_IDS

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    return "Kesha OK"


def _session_ids(data):
    s = data.get("session") or {}
    ids = [(s.get("user") or {}).get("user_id"),
           (s.get("application") or {}).get("application_id"),
           s.get("user_id")]
    return [i for i in ids if i]


@app.route("/alice", methods=["POST"])
def alice_skill():
    try:
        data = request.json
        ids = _session_ids(data)
        if not ALICE_ALLOWED_IDS.intersection(ids):
            print("[alice] отказано, ids=%s (добавьте нужный в ALICE_ALLOWED_IDS)" % ids)
            return jsonify({
                "response": {"text": "Доступ запрещён.", "end_session": True},
                "version": data.get("version", "1.0"),
                "session": data.get("session", {}),
            })
        text = data["request"]["original_utterance"].strip() or "привет"
        reply = handle_command(text, source="alice")
        return jsonify({
            "response": {"text": reply or "Готов помочь.", "end_session": False},
            "version": data.get("version", "1.0"),
            "session": data.get("session", {}),
        })
    except Exception as e:
        print("[alice]", e)
        return jsonify({
            "response": {"text": "Ошибка", "end_session": True},
            "version": "1.0", "session": {},
        })


def _run_ngrok():
    import threading, time, requests

    NGROK_API = "http://127.0.0.1:4040/api/tunnels"

    def _is_running():
        try:
            r = requests.get(NGROK_API, timeout=1)
            return r.status_code == 200 and len(r.json().get("tunnels", [])) > 0
        except Exception:
            return False

    def _get_public_url():
        try:
            r = requests.get(NGROK_API, timeout=2)
            for t in r.json().get("tunnels", []):
                if t.get("proto") == "https":
                    return t.get("public_url")
        except Exception:
            pass
        return None

    def _launch():
        if _is_running():
            url = _get_public_url()
            print("[ngrok] уже запущен:", url or "туннель есть, URL не получен")
            return

        if not shutil.which("ngrok"):
            print("[ngrok] не установлен — https://ngrok.com/download")
            return

        try:
            flags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                flags = subprocess.CREATE_NO_WINDOW
            subprocess.Popen(
                ["ngrok", "http", str(ALICE_PORT)],
                creationflags=flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("[ngrok] запускаю туннель на порт", ALICE_PORT)

            for _ in range(15):
                time.sleep(1)
                url = _get_public_url()
                if url:
                    print("[ngrok] публичный URL:", url)
                    print("[ngrok] → webhook для Алисы:", url + "/alice")
                    return
            print("[ngrok] не удалось получить URL за 15 сек")
        except Exception as e:
            print("[ngrok] ошибка:", e)

    threading.Thread(target=_launch, daemon=True).start()



def start_alice():
    _run_ngrok()
    print("[alice] http://%s:%s/alice" % (ALICE_HOST, ALICE_PORT))
    print("[alice] ngrok http", ALICE_PORT)
    app.run(host=ALICE_HOST, port=ALICE_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    start_alice()
