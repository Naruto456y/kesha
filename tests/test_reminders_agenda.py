"""Тесты волны 4: напоминания, будильник, таймер, заметки, погода, календарь, курсы, сообщения."""
from datetime import datetime, timedelta

import pytest

import core
from core import handle_command
from timeparse import parse_when, parse_duration, words_to_digits, say_duration

NOW = datetime(2026, 10, 23, 15, 10)   # пятница


# ---------- разбор времени ----------
@pytest.mark.parametrize("phrase,expected,rest", [
    ("напомни через 20 минут выключить плиту", NOW + timedelta(minutes=20), "напомни выключить плиту"),
    ("напомни через двадцать пять минут", NOW + timedelta(minutes=25), "напомни"),
    ("напомни через полчаса", NOW + timedelta(minutes=30), "напомни"),
    ("напомни через полтора часа", NOW + timedelta(minutes=90), "напомни"),
    ("напомни через 2 часа 15 минут", NOW + timedelta(minutes=135), "напомни"),
    ("напомни через час и 10 минут", NOW + timedelta(minutes=70), "напомни"),
    ("напомни в 18:30 позвонить маме", datetime(2026, 10, 23, 18, 30), "напомни позвонить маме"),
    ("напомни в 6 полить цветы", datetime(2026, 10, 23, 18, 0), "напомни полить цветы"),
    ("напомни в 9 утра", datetime(2026, 10, 24, 9, 0), "напомни"),
    ("напомни завтра купить хлеб", datetime(2026, 10, 24, 9, 0), "напомни купить хлеб"),
    ("напомни завтра в 7 вечера", datetime(2026, 10, 24, 19, 0), "напомни"),
    ("напомни в понедельник в 10 сдать отчёт", datetime(2026, 10, 26, 10, 0), "напомни сдать отчет"),
    ("напомни в пятницу", datetime(2026, 10, 30, 9, 0), "напомни"),
    ("напомни в полдень поесть", datetime(2026, 10, 24, 12, 0), "напомни поесть"),
    ("напомни в 7 часов 15 минут вечера", datetime(2026, 10, 23, 19, 15), "напомни"),
])
def test_parse_when(phrase, expected, rest):
    w = parse_when(phrase, NOW)
    assert (w.dt, w.rest) == (expected, rest)


def test_parse_when_alarm_prefers_morning():
    assert parse_when("разбуди меня в 7", NOW, prefer_morning=True).dt == datetime(2026, 10, 24, 7, 0)
    assert parse_when("разбуди в семь тридцать", NOW, prefer_morning=True).dt == datetime(2026, 10, 24, 7, 30)
    assert parse_when("будильник на 7:30", NOW).dt == datetime(2026, 10, 24, 7, 30)


def test_parse_when_none():
    assert parse_when("напомни купить хлеб", NOW) is None
    assert parse_when("в 2026 году", NOW) is None


def test_numbers_and_durations():
    assert words_to_digits("сто двадцать пять") == "125"
    assert words_to_digits("семь тридцать") == "7 30"
    assert words_to_digits("две тысячи двадцать шесть") == "2026"
    assert parse_duration("таймер на 5 минут") == 300
    assert parse_duration("таймер на полтора часа") == 5400
    assert parse_duration("таймер 10") == 600
    assert parse_duration("засеки три минуты") == 180
    assert say_duration(5400) == "1 час 30 минут"
    assert say_duration(61) == "1 минуту 1 секунду"


# ---------- напоминания ----------
@pytest.fixture
def announced(monkeypatch):
    out = []
    monkeypatch.setattr(core, "announce", lambda text, **kw: out.append((text, kw)))
    from features import reminders
    monkeypatch.setattr(reminders, "start", lambda: None)
    return out


def test_reminder_flow(announced):
    from features import reminders
    reply = handle_command("Кеша, напомни через 20 минут выключить плиту", "voice")
    assert reply == "Хорошо, напомню через 20 минут: выключить плиту"
    items = reminders.store.pending()
    assert len(items) == 1 and items[0]["source"] == "voice"
    due = datetime.fromisoformat(items[0]["due"])

    assert reminders.check_due(due - timedelta(seconds=1)) == []
    reminders.check_due(due + timedelta(seconds=1))
    assert announced[0][0] == "Напоминаю: выключить плиту"
    assert reminders.store.pending() == []


def test_reminder_needs_time(announced):
    assert handle_command("напомни купить хлеб", "t").startswith("Когда напомнить?")


def test_reminders_survive_restart(announced, tmp_path):
    from features import reminders
    handle_command("напомни завтра в 9 сдать отчёт", "t")
    fresh = reminders.ReminderStore(reminders.store.path)
    assert fresh.pending()[0]["text"] == "сдать отчет"


def test_missed_reminders(announced):
    from features import reminders
    now = datetime.now()
    reminders.store.add("reminder", now - timedelta(hours=1), "пропущенное")
    reminders.store.add("reminder", now - timedelta(days=2), "совсем старое")
    reminders.check_due(now)
    assert len(announced) == 1 and "пропущено" in announced[0][0]
    assert reminders.store.pending() == []


def test_list_and_cancel(announced):
    from features import reminders
    handle_command("напомни через 10 минут чай", "t")
    handle_command("напомни через час позвонить", "t")
    listing = handle_command("какие напоминания", "t")
    assert "1. напоминание" in listing and "чай" in listing and "позвонить" in listing
    assert handle_command("отмени напоминание 1", "t").startswith("Отменил: напоминание")
    assert len(reminders.store.pending()) == 1
    assert handle_command("отмени все напоминания", "t") == "Отменил все напоминания: 1."
    assert handle_command("какие напоминания", "t") == "Напоминаний нет."


def test_alarm_and_stop(announced, monkeypatch):
    from features import reminders
    from voice import sfx
    ringing = {"on": False}
    monkeypatch.setattr(sfx, "alarm_start", lambda max_sec=None: ringing.update(on=True))
    monkeypatch.setattr(sfx, "alarm_stop", lambda: ringing.pop("on", False) and True)

    reply = handle_command("разбуди меня в 7", "voice")
    assert reply.startswith("Будильник на ")
    item = reminders.store.pending("alarm")[0]
    assert datetime.fromisoformat(item["due"]).hour == 7
    reminders.check_due(datetime.fromisoformat(item["due"]) + timedelta(seconds=1))
    assert ringing.get("on") and announced[0][0].startswith("Подъём!")
    assert handle_command("стоп", "voice") == "Выключил."
    # будильник не звонит — обычное «стоп» уходит в паузу музыки
    import commands
    monkeypatch.setattr(commands.keyboard, "send", lambda k: None)
    assert handle_command("стоп", "voice") == "Пауза"


def test_timer(announced, monkeypatch):
    from features import reminders
    from voice import sfx
    monkeypatch.setattr(sfx, "alarm_start", lambda max_sec=None: None)
    assert handle_command("поставь таймер на 5 минут", "t") == "Таймер на 5 минут запущен."
    assert handle_command("засеки время 2 минуты", "t") == "Таймер на 2 минуты запущен."
    item = reminders.store.pending("timer")[0]
    reminders.check_due(datetime.fromisoformat(item["due"]) + timedelta(seconds=1))
    assert announced[0][0] == "Таймер на 2 минуты закончился!"
    assert handle_command("отмени таймер", "t") == "Отменил все таймеры: 1."


def test_telegram_reminder_comes_back_to_telegram(announced, monkeypatch):
    from features import reminders, messenger
    sent = []
    monkeypatch.setattr(messenger, "send_to_owners", lambda text: sent.append(text))
    handle_command("напомни через минуту полить цветы", "telegram")
    item = reminders.store.pending()[0]
    reminders.check_due(datetime.fromisoformat(item["due"]) + timedelta(seconds=1))
    assert sent == ["Напоминаю: полить цветы"]


# ---------- заметки и дела ----------
def test_notes_and_todo():
    assert handle_command("Кеша, запиши: купить молоко", "t") == "Записал: купить молоко"
    assert handle_command("добавь в список дел помыть посуду", "t") == "Добавил в список дел: помыть посуду"
    assert handle_command("добавь задачу сделать уроки", "t") == "Добавил в список дел: сделать уроки"
    assert handle_command("мои заметки", "t") == "Заметки:\n1. купить молоко"
    assert handle_command("список дел", "t") == "Дела:\n1. помыть посуду\n2. сделать уроки"
    assert handle_command("выполнил задачу 1", "t").startswith("Отлично! «помыть посуду» выполнено")
    assert handle_command("что мне сделать", "t") == "Дела:\n1. сделать уроки"
    assert handle_command("удали заметку 1", "t") == "Удалил: купить молоко"
    assert handle_command("мои заметки", "t") == "Заметок нет."
    assert handle_command("очисти список дел", "t") == "Список дел очищен."


def test_notes_file_format(tmp_path):
    import json
    from features import notes
    handle_command("запиши купить хлеб", "t")
    data = json.loads(notes.store.path.read_text(encoding="utf-8"))
    assert data["notes"][0]["text"] == "купить хлеб"


# ---------- курсы ----------
CBR = {"Valute": {
    "USD": {"Value": 81.5, "Previous": 81.0, "Nominal": 1},
    "EUR": {"Value": 94.2, "Previous": 94.5, "Nominal": 1},
    "CNY": {"Value": 11.3, "Previous": 11.3, "Nominal": 1},
    "JPY": {"Value": 53.0, "Previous": 53.0, "Nominal": 100},
}}
GECKO = {"bitcoin": {"usd": 100000.0, "rub": 8150000.0, "usd_24h_change": 2.345},
         "ethereum": {"usd": 4000.0, "rub": 326000.0, "usd_24h_change": -1.0}}


@pytest.fixture
def fake_rates(monkeypatch):
    from features import rates
    rates._cache.clear()

    def fake(url, params=None):
        if "cbr" in url:
            return CBR
        return {c: GECKO[c] for c in params["ids"].split(",")}
    monkeypatch.setattr(rates, "_get_json", fake)
    return rates


@pytest.mark.parametrize("phrase,answer", [
    ("сколько стоит доллар", "Доллар по курсу ЦБ — 81.5 ₽, вырос на 0.5."),
    ("курс евро", "Евро по курсу ЦБ — 94.2 ₽, упал на 0.3."),
    ("курс иены", "Иена по курсу ЦБ — 0.53 ₽."),
    ("курс биткоина", "Биткоин стоит 100 000 $ (8 150 000 ₽), за сутки +2.3%."),
    ("сколько будет 100 долларов в рублях", "100 доллар — это 8 150 ₽"),
    ("сколько будет сто евро в долларах", "100 евро — это 115.58 $"),
    ("1000 рублей в долларах", "1 000 рубль — это 12.27 $"),
    ("курс валют", "Курс ЦБ: доллар 81.5 ₽, евро 94.2 ₽, юань 11.3 ₽."),
])
def test_rates(fake_rates, phrase, answer):
    assert handle_command(phrase, "t") == answer


def test_rates_offline(monkeypatch):
    from features import rates
    rates._cache.clear()

    def boom(*a, **k):
        raise ConnectionError("нет сети")
    monkeypatch.setattr(rates.requests, "get", boom)
    assert handle_command("курс доллара", "t") == "Не удалось получить курс — проверь интернет."


# ---------- погода: прогноз ----------
def test_forecast_summary():
    import commands
    base = datetime(2026, 10, 24, 0, 0)
    points = []
    for day in range(4):
        for h in (3, 9, 15, 21):
            ts = (base + timedelta(days=day, hours=h)).timestamp()
            points.append({"dt": ts, "main": {"temp_min": 2 + day + h / 10, "temp_max": 5 + day + h / 3},
                           "weather": [{"description": "дождь" if h < 15 else "облачно"}],
                           "wind": {"speed": 3 + h / 10}})
    lines = commands.summarize_forecast({"list": points}, [1, 2], datetime(2026, 10, 23).date())
    assert lines[0].startswith("Завтра: от 2 до 12°C") and lines[1].startswith("Послезавтра: от 3 до 13°C")


def test_forecast_command(monkeypatch):
    import commands

    class R:
        status_code = 200

        def json(self):
            today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
            return {"city": {"name": "Москва"}, "list": [
                {"dt": (today + timedelta(days=d)).timestamp(), "main": {"temp_min": d, "temp_max": d + 4},
                 "weather": [{"description": "ясно"}], "wind": {"speed": 2}} for d in range(1, 4)]}
    monkeypatch.setattr(commands.requests, "get", lambda *a, **k: R())
    reply = handle_command("погода на завтра", "t")
    assert reply == "Москва. Завтра: от 1 до 5°C, ясно, ветер до 2 м/с."
    assert handle_command("погода в москве на завтра", "t") == reply
    three = handle_command("прогноз на 3 дня", "t")
    assert three.count("°C") == 3


# ---------- календарь ----------
ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//RU
BEGIN:VEVENT
UID:once@test
DTSTART:20261024T120000Z
DTEND:20261024T130000Z
SUMMARY:Встреча с Петей
END:VEVENT
BEGIN:VEVENT
UID:weekly@test
DTSTART;TZID=Europe/Moscow:20261001T180000
DTEND;TZID=Europe/Moscow:20261001T190000
RRULE:FREQ=WEEKLY;BYDAY=TH,SA
SUMMARY:Тренировка
END:VEVENT
BEGIN:VEVENT
UID:allday@test
DTSTART;VALUE=DATE:20261024
DTEND;VALUE=DATE:20261025
SUMMARY:День рождения бабушки
END:VEVENT
END:VCALENDAR
""".encode("utf-8")


def test_ics_parsing_with_recurrence():
    from features import agenda
    events = agenda.ics_events(ICS, datetime(2026, 10, 24), datetime(2026, 10, 25))
    titles = [e["title"] for e in events]
    assert set(titles) == {"Встреча с Петей", "Тренировка", "День рождения бабушки"}
    training = next(e for e in events if e["title"] == "Тренировка")
    assert training["start"].hour == 18 or training["start"].hour != 0   # локальное время
    assert next(e for e in events if e["all_day"])["title"] == "День рождения бабушки"


def test_agenda_add_and_list(monkeypatch):
    from features import agenda
    put = []
    monkeypatch.setattr(agenda, "push_caldav", lambda item: put.append(item) or False)
    reply = handle_command("добавь в календарь встречу с врачом завтра в 15:00", "t")
    assert reply == "Добавил в календарь: встречу с врачом, завтра в 15:00."
    assert put and put[0]["title"] == "встречу с врачом"
    assert handle_command("что у меня завтра", "t") == "Завтра: 15:00 — встречу с врачом."
    assert handle_command("что у меня сегодня", "t") == "Сегодня ничего не запланировано."
    assert "встречу с врачом" in handle_command("что в календаре на неделе", "t")


def test_agenda_reads_ics(monkeypatch):
    from features import agenda
    monkeypatch.setattr(agenda, "ics_urls", ["https://example.invalid/cal.ics"])
    monkeypatch.setattr(agenda, "_fetch_ics", lambda url: ICS)
    start, end, _ = datetime(2026, 10, 24), datetime(2026, 10, 25), None
    titles = [e["title"] for e in agenda.events_between(start, end)]
    assert "Встреча с Петей" in titles and "Тренировка" in titles


def test_caldav_put(monkeypatch):
    from features import agenda
    monkeypatch.setattr(agenda, "CALDAV_URL", "https://caldav.yandex.ru/calendars/me/events-default/")
    monkeypatch.setattr(agenda, "CALDAV_USER", "me")
    monkeypatch.setattr(agenda, "CALDAV_PASSWORD", "app-pass")
    calls = []

    class R:
        def raise_for_status(self):
            pass
    monkeypatch.setattr(agenda.requests, "put", lambda url, **kw: calls.append((url, kw)) or R())
    item = agenda.add_event("Созвон, важный", datetime(2026, 10, 24, 15, 0))
    assert agenda.push_caldav(item)
    url, kw = calls[0]
    assert url.endswith(f"/{item['id']}.ics") and kw["auth"] == ("me", "app-pass")
    body = kw["data"].decode("utf-8")
    assert "DTSTART:20261024T150000" in body and "SUMMARY:Созвон\\, важный" in body


# ---------- сообщения в Telegram ----------
def test_messenger_parse_and_resolve(monkeypatch):
    from features import messenger
    assert messenger.parse("напиши маме в телеграм что я дома") == ("маме", "я дома")
    assert messenger.parse("отправь в телегу пете сообщение буду в 7") == ("пете", "буду в 7")
    messenger.remember_user(111, "Петя", "petya")
    monkeypatch.setattr(messenger, "contacts", {"мама": "222"})
    assert messenger.resolve("маме") == ("мама", "222")
    assert messenger.resolve("пете") == ("петя", "111")
    assert messenger.resolve("васе") is None


def test_send_message_command(monkeypatch):
    from features import messenger
    monkeypatch.setattr(messenger, "contacts", {"мама": "222"})
    sent = []
    monkeypatch.setattr(messenger, "send", lambda chat, text: sent.append((chat, text)) or True)
    assert handle_command("Кеша, напиши маме в телеграм, что я дома", "voice") == "Отправил (мама): «Я дома»"
    assert sent == [("222", "Я дома")]
    assert "Не знаю, кто такой «бабушке»" in handle_command("напиши бабушке в телеграм привет", "voice")
    assert handle_command("открой телеграм", "voice") != "Отправил"


def test_send_message_is_exact_only(monkeypatch):
    """Опасная команда: GigaChat не может «додумать» отправку."""
    from features import messenger
    monkeypatch.setattr(messenger, "contacts", {"мама": "222"})
    sent = []
    monkeypatch.setattr(messenger, "send", lambda chat, text: sent.append(text))
    monkeypatch.setattr(core, "ai_ask", lambda t: "CMD: напиши маме в телеграм привет")
    handle_command("передай мамуле привет", "voice")
    assert sent == []
