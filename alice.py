import subprocess
import shutil
"""Навык Алисы - Flask."""
from flask import Flask, request, jsonify
from core import handle_command
from config import ALICE_HOST, ALICE_PORT

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    return "Kesha OK"


@app.route("/alice", methods=["POST"])
def alice_skill():
    try:
        data = request.json
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
    import threading
    if not shutil.which("ngrok"):
        print("[ngrok] не установлен, пропускаем")
        return
    def _launch():
        try:
            subprocess.Popen(["ngrok", "http", str(ALICE_PORT)],
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
            print("[ngrok] запущен на порту", ALICE_PORT)
        except Exception as e:
            print("[ngrok]", e)
    threading.Thread(target=_launch, daemon=True).start()


def start_alice():
    _run_ngrok()
    print("[alice] http://%s:%s/alice" % (ALICE_HOST, ALICE_PORT))
    print("[alice] ngrok http", ALICE_PORT)
    app.run(host=ALICE_HOST, port=ALICE_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    start_alice()
