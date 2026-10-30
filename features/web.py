"""
Сайты одной фразой: почта, Озон, «открой первую ссылку», «спроси …» (ответ ИИ).

    «открой почту»                     -> e.mail.ru/inbox
    «найди на озоне наушники»          -> поиск Озона
    «открой первую ссылку котики»      -> сразу первый результат поиска
    «найди рецепт борща и открой первую ссылку» — то же
    «спроси, почему небо голубое»      -> ответ GigaChat, без поиска команд
"""
import re
import webbrowser
from urllib.parse import quote

import requests

import core
from core import registry

MAIL_URL = "https://e.mail.ru/inbox/"
OZON_SEARCH = "https://www.ozon.ru/search/?text={}"
BING_SEARCH = "https://www.bing.com/search"
DDG_LUCKY = "https://duckduckgo.com/?q=%5C{}"
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
_last_query = ""          # последний поиск — для «открой первую ссылку» без запроса


def _strip(text, words):
    q = text.lower()
    for w in sorted(words, key=len, reverse=True):
        q = re.sub(rf"(?<!\w){re.escape(w)}(?!\w)", " ", q)
    return " ".join(q.replace(",", " ").split())


# ---------- почта ----------
@registry.command(
    ["открой почту", "почта", "моя почта", "открой мейл", "открой mail", "открой майл",
     "проверь почту", "покажи почту", "входящие", "открой входящие", "зайди в почту",
     "открой электронную почту", "мейл ру", "mail ru"],
    "Открыть почту Mail.ru", "Интернет", priority=14,
)
def open_mail(text):
    webbrowser.open(MAIL_URL)
    return "Открываю почту"


# ---------- Озон ----------
_OZON_WORDS = ["найди на озоне", "поищи на озоне", "найди в озоне", "поищи в озоне",
               "закажи на озоне", "купи на озоне", "посмотри на озоне", "озон найди",
               "на озоне", "в озоне", "озон", "ozon"]


@registry.command(
    _OZON_WORDS + ["открой озон", "добавь в корзину", "положи в корзину", "добавь в корзину озон"],
    "Поиск товаров на Озоне", "Интернет", priority=13,
)
def ozon(text):
    query = _strip(text, _OZON_WORDS + ["открой", "добавь в корзину", "положи в корзину", "корзину",
                                        "найди", "поищи", "купи", "закажи"])
    if not query:
        webbrowser.open("https://www.ozon.ru/")
        return "Открываю Озон"
    webbrowser.open(OZON_SEARCH.format(quote(query)))
    if "корзин" in text:
        # в корзину кладёт только твой аккаунт Озона — сам не нажимаю, чтобы не купить не то
        return f"Нашёл на Озоне «{query}». Выбери товар и нажми «В корзину»."
    return f"Ищу на Озоне: {query}"


# ---------- первая ссылка ----------
_FIRST_WORDS = ["открой первую ссылку", "открой первый сайт", "открой первый результат",
                "перейди по первой ссылке", "первую ссылку", "первая ссылка", "первый сайт",
                "первый результат"]
_SEARCH_LEAD = ["найди в интернете", "поищи в интернете", "найди", "поищи", "загугли", "погугли", "и"]


def _bing_target(href):
    """Ссылки Bing идут через bing.com/ck/a?...&u=a1<base64 адреса> — достаём настоящий адрес."""
    import base64
    from html import unescape
    from urllib.parse import parse_qs, urlparse
    href = unescape(href)
    u = parse_qs(urlparse(href).query).get("u", [""])[0]
    if u.startswith("a1"):
        raw = u[2:] + "=" * (-len(u[2:]) % 4)
        try:
            return base64.urlsafe_b64decode(raw).decode("utf-8")
        except Exception:
            return None
    return href if "bing.com" not in href else None


def first_result(query):
    """Адрес первого результата поиска (Bing: без ключей и без капчи, в отличие от Яндекса
    и DuckDuckGo для скриптов). Нет сети — None."""
    try:
        r = requests.get(BING_SEARCH, params={"q": query, "setlang": "ru"}, timeout=6, headers=_UA)
        for href in re.findall(r'<li class="b_algo".*?<a[^>]+href="(https?://[^"]+)"', r.text, re.S):
            url = _bing_target(href)
            if url and url.startswith("http"):
                return url
    except Exception as e:
        print(f"[first_link] {e}")
    return None


@registry.command(_FIRST_WORDS, "Открыть первую ссылку поиска", "Интернет", priority=16)
def open_first_link(text):
    global _last_query
    query = _strip(text, _FIRST_WORDS + _SEARCH_LEAD) or _last_query
    if not query:
        return "Что найти?"
    _last_query = query
    return open_first(query)


def open_first(query):
    url = first_result(query)
    if not url:
        # Bing иногда отдаёт скрипту страницу без результатов; «\запрос» в DuckDuckGo
        # (I'm Feeling Ducky) в обычном браузере сразу переходит на первый результат
        url = DDG_LUCKY.format(quote(query))
    webbrowser.open(url)
    return "Открываю первую ссылку"


def remember_search(query):
    """search_web зовёт: потом «открой первую ссылку» без запроса возьмёт его."""
    global _last_query
    _last_query = query


# ---------- спроси ----------
_ASK_WORDS = ["спроси у нейросети", "спроси у гигачата", "спроси у ии", "спроси нейросеть",
              "спроси гигачат", "спроси ии", "спроси у чата", "спроси"]


@registry.command(_ASK_WORDS, "Спросить ИИ (короткий ответ)", "Основные", priority=40)
def ask_ai(text):
    question = _strip(text, _ASK_WORDS)
    if not question:
        return "Что спросить?"
    return core.ai_answer(question)
