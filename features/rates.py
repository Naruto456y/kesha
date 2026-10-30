"""
Курсы валют и криптовалют (волна 4). Без ключей:
  валюты — ЦБ РФ (cbr-xml-daily.ru), крипта — CoinGecko.

    «сколько стоит доллар», «курс евро», «курс биткоина»,
    «сколько будет 100 долларов в рублях»
Ответы кэшируются на 10 минут.
"""

import re
import threading
import time

import requests

from core import registry
from timeparse import words_to_digits

CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
GECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
CACHE_SEC = 600

# основа слова -> (код, как назвать в ответе)
CURRENCIES = [
    (r"доллар|бакс|usd", "USD", "доллар"),
    (r"евро\b|eur", "EUR", "евро"),
    (r"юан|cny", "CNY", "юань"),
    (r"фунт|gbp", "GBP", "фунт"),
    (r"иен|йен|jpy", "JPY", "иена"),
    (r"лир[аыу]?\b|турецк", "TRY", "лира"),
    (r"тенге|kzt", "KZT", "тенге"),
    (r"белорусск|byn", "BYN", "белорусский рубль"),
    (r"гривн|uah", "UAH", "гривна"),
    (r"франк|chf", "CHF", "франк"),
    (r"дирхам|aed", "AED", "дирхам"),
]
CRYPTO = [
    (r"биткоин|биткойн|битк|btc|bitcoin", "bitcoin", "биткоин"),
    (r"эфир|эфириум|ethereum|eth\b", "ethereum", "эфир"),
    (r"тон\b|тонкоин|toncoin|\bton\b", "the-open-network", "TON"),
    (r"солан|solana", "solana", "Solana"),
    (r"доги|догикоин|dogecoin|додж", "dogecoin", "Dogecoin"),
    (r"тезер|tether|usdt", "tether", "USDT"),
]

_cache = {}
_lock = threading.Lock()


def _get_json(url, params=None):
    key = (url, tuple(sorted((params or {}).items())))
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < CACHE_SEC:
            return hit[1]
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    with _lock:
        _cache[key] = (time.time(), data)
    return data


def cbr_rate(code):
    """Рублей за 1 единицу валюты (ЦБ учитывает номинал: иена — за 100)."""
    v = _get_json(CBR_URL)["Valute"][code]
    return v["Value"] / v["Nominal"], v["Value"] - v["Previous"]


def crypto_price(coin):
    data = _get_json(GECKO_URL, {"ids": coin, "vs_currencies": "usd,rub",
                                 "include_24hr_change": "true"})[coin]
    return data["usd"], data["rub"], data.get("usd_24h_change")


_RUB = (r"рубл|руб\b|rub", "RUB", "рубль")


def _find(table, text):
    for rx, code, name in table:
        if re.search(r"(?<!\w)(?:" + rx + ")", text):
            return code, name
    return None


def _mentions(text):
    """Все упоминания валют/крипты по порядку: [(позиция, код, название, крипта?)]."""
    found = []
    for table, is_coin in ((CURRENCIES, False), (CRYPTO, True), ([_RUB], False)):
        for rx, code, name in table:
            m = re.search(r"(?<!\w)(?:" + rx + ")", text)
            if m:
                found.append((m.start(), code, name, is_coin))
    return sorted(found)


def _rub_per_unit(code, is_coin):
    if code == "RUB":
        return 1.0
    if is_coin:
        return crypto_price(code)[1]
    return cbr_rate(code)[0]


def _money(x):
    if x >= 1000:
        return f"{x:,.0f}".replace(",", " ")
    if x >= 10:
        return f"{x:.2f}".rstrip("0").rstrip(".")
    return f"{x:.4f}".rstrip("0").rstrip(".")


def _trend(delta):
    if delta is None or abs(delta) < 1e-9:
        return ""
    return f", {'вырос' if delta > 0 else 'упал'} на {abs(delta):.2f}".rstrip("0").rstrip(".")


@registry.command(
    ["курс", "сколько стоит доллар", "сколько стоит евро", "почем доллар", "почём доллар",
     "курс валют", "курс доллара", "курс евро", "курс юаня", "курс биткоина",
     "сколько стоит биткоин", "биткоин", "биткойн", "курс крипты", "крипта",
     "сколько стоит эфир", "в рублях", "в рубли", "в долларах"],
    "Курс валют и крипты", "Финансы", priority=4,
)
def rates(text):
    t = words_to_digits(text.lower().replace("ё", "е"))
    m = re.search(r"\b(\d+(?:[.,]\d+)?)\b", t)
    amount = float(m.group(1).replace(",", ".")) if m else None
    mentions = _mentions(t)
    try:
        # «100 долларов в рублях», «1000 рублей в евро», «2 биткоина в долларах»
        if amount is not None and len(mentions) >= 2:
            (_, src, src_name, src_coin), (_, dst, dst_name, dst_coin) = mentions[:2]
            if src_coin and dst == "USD":
                value = amount * crypto_price(src)[0]
            else:
                value = amount * _rub_per_unit(src, src_coin) / _rub_per_unit(dst, dst_coin)
            sym = {"RUB": "₽", "USD": "$"}.get(dst, dst_name)
            return f"{_money(amount)} {src_name} — это {_money(value)} {sym}"

        coin = _find(CRYPTO, t)
        if coin:
            usd, rub, change = crypto_price(coin[0])
            tail = f", за сутки {change:+.1f}%" if change is not None else ""
            return f"{coin[1].capitalize()} стоит {_money(usd)} $ ({_money(rub)} ₽){tail}."
        cur = _find(CURRENCIES, t)
        if cur:
            rate, delta = cbr_rate(cur[0])
            if amount is not None:
                return f"{_money(amount)} {cur[1]} — это {_money(amount * rate)} ₽"
            return f"{cur[1].capitalize()} по курсу ЦБ — {_money(rate)} ₽{_trend(delta)}."
        if "курс" in t or "валют" in t or "крипт" in t:
            if "крипт" in t:
                btc, eth = crypto_price("bitcoin")[0], crypto_price("ethereum")[0]
                return f"Биткоин {_money(btc)} $, эфир {_money(eth)} $."
            usd, _ = cbr_rate("USD")
            eur, _ = cbr_rate("EUR")
            cny, _ = cbr_rate("CNY")
            return f"Курс ЦБ: доллар {_money(usd)} ₽, евро {_money(eur)} ₽, юань {_money(cny)} ₽."
    except Exception as e:
        print(f"[rates] {e}")
        return "Не удалось получить курс — проверь интернет."
    return None
