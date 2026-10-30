"""
Отправка сообщений (волна 4): «Кеша, напиши маме в телеграм, что я дома».

Шлёт через того же Telegram-бота (TELEGRAM_TOKEN). Кому — ищем:
  1) в TELEGRAM_CONTACTS из .env:   TELEGRAM_CONTACTS=мама:123456789,папа:987654321
  2) среди тех, кто писал боту (data/telegram_users.json — бот запоминает имя и id).
Telegram разрешает боту писать только тем, кто хоть раз написал ему сам.
Команда опасная (risky): только точной фразой, без угадываний.
"""

import json
import os
import re
import threading

import requests

from config import (TELEGRAM_TOKEN, TELEGRAM_CONTACTS, TELEGRAM_ALLOWED_IDS,
                    TELEGRAM_USERS_FILE)
from core import registry

API = "https://api.telegram.org/bot{token}/sendMessage"
_lock = threading.Lock()
users_file = TELEGRAM_USERS_FILE
contacts = dict(TELEGRAM_CONTACTS)


# ---------- кто писал боту ----------
def _load_users():
    try:
        with open(users_file, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def remember_user(user_id, first_name="", username=""):
    """Бот вызывает это на каждое входящее сообщение."""
    with _lock:
        users = _load_users()
        entry = {"first_name": first_name or "", "username": username or ""}
        if users.get(str(user_id)) == entry:
            return
        users[str(user_id)] = entry
        tmp = f"{users_file}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        os.replace(tmp, users_file)


def known_contacts() -> dict:
    """имя (в нижнем регистре) -> chat_id."""
    out = {}
    for uid, u in _load_users().items():
        for name in (u.get("first_name"), u.get("username")):
            if name:
                out[name.lower()] = uid
    out.update(contacts)
    return out


def _nominatives(word):
    """«маме» -> мама, «пете» -> петя, «ивану» -> иван, «игорю» -> игорь."""
    w = word.lower().replace("ё", "е")
    stem = w[:-1]
    return [w, stem + "а", stem + "я", stem, stem + "ь", stem + "й", w[:-2] + "а"]


def resolve(word):
    book = known_contacts()
    for form in _nominatives(word):
        if form in book:
            return form, book[form]
    return None


# ---------- отправка ----------
def send(chat_id, text) -> bool:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN не задан")
    r = requests.post(API.format(token=TELEGRAM_TOKEN),
                      json={"chat_id": chat_id, "text": text}, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(r.json().get("description", f"HTTP {r.status_code}"))
    return True


def send_to_owners(text):
    """Владельцам бота (TELEGRAM_ALLOWED_IDS) — например, сработавшее напоминание."""
    for uid in TELEGRAM_ALLOWED_IDS:
        try:
            send(uid, text)
        except Exception as e:
            print(f"[messenger] {uid}: {e}")


_CHANNEL = r"(?:в|через|по)\s+(?:телеграмм?[еу]?|телег[уеи]|telegram)"
_VERB = r"^(?:напиши|отправь|скинь|передай|скажи|сообщи|черкни|отпиши)\s+"
_FILLER = {"что", "сообщение", "-", "мол", "пожалуйста"}


def parse(text):
    """-> (получатель, сообщение) или None."""
    t = " ".join(re.sub(_CHANNEL, " ", text.lower(), count=1).split())
    t = re.sub(_VERB, "", t)
    t = re.sub(r"^сообщение\s+", "", t)
    words = t.replace(",", " ").replace(":", " ").split()
    if len(words) < 2:
        return None
    recipient, rest = words[0], words[1:]
    while rest and rest[0] in _FILLER:
        rest.pop(0)
    if not rest:
        return None
    return recipient, " ".join(rest)


@registry.command(
    ["в телеграм", "в телеграмм", "в телеграме", "в телегу", "в телеге", "через телеграм",
     "по телеграму", "в telegram"],
    "Отправить сообщение в Telegram", "Связь", priority=12, risky=True,   # выше «напиши» (печать)
)
def send_message(text):
    if not re.search(r"\b(напиши|отправь|скинь|передай|скажи|сообщи|черкни|отпиши|сообщение)\b", text):
        return None   # «открой телеграм» и т.п. — не наше
    parsed = parse(text)
    if parsed is None:
        return "Кому и что написать? Например: «напиши маме в телеграм, что я дома»."
    who, message = parsed
    found = resolve(who)
    if found is None:
        return (f"Не знаю, кто такой «{who}». Добавь в .env строку "
                f"TELEGRAM_CONTACTS={who}:<chat_id> — id покажет бот, если человек ему напишет.")
    name, chat_id = found
    message = message[0].upper() + message[1:]
    try:
        send(chat_id, message)
    except Exception as e:
        return f"Не удалось отправить: {e}"
    return f"Отправил ({name}): «{message}»"
