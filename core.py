"""
Ядро проекта Кеша.
Реестр команд + handle_command + шина событий + AI fallback.

Конвейер распознавания handle_command (волна 2):
  1. точное совпадение паттерна
  2. синонимы        («вруби лампу»  -> «включи лампу»)
  3. follow-up       («а в Питере?»  -> «погода в питере»)
  4. нечёткий поиск  (опечатки, искажения распознавания)
  5. GigaChat        (перефразировать в команду ИЛИ ответить на вопрос)
Шаги 2–5 никогда не запускают опасные команды (risky=True) —
их можно вызвать только точной фразой.
"""

from dotenv import load_dotenv
load_dotenv()  # загружаем .env из корня проекта

import contextvars
import re
import time

import klog
import persona
import session
import settings
from ai_cache import cache as ai_cache
from config import WAKE_WORDS, AI_COMMANDS_MAX_WORDS, AI_MAX_WORDS, AI_FIX_COMMANDS, AI_FIX_MAX_WORDS
from nlu import (normalize, apply_synonyms, fuzzy_find, is_question, has_negation,
                 has_latin, fix_mixed_script)


# ============================================================
#  РЕЕСТР КОМАНД
# ============================================================
class CommandRegistry:
    """Хранит все команды проекта.
    Каждая команда регистрируется через декоратор @registry.command(...)"""

    def __init__(self):
        self.commands = []

    def command(self, patterns, description="", category="Общее", priority=0,
                risky=False, followup=None):
        """risky   — опасная команда: только точная фраза, без fuzzy/синонимов/GigaChat.
        followup — шаблон уточнения для «а в Питере?», например "погода в {arg}"."""
        def decorator(func):
            lowered = [p.lower() for p in patterns]
            alternatives = "|".join(re.escape(p) for p in sorted(lowered, key=len, reverse=True))
            self.commands.append({
                "patterns": lowered,
                "regex": re.compile(r"\b(?:" + alternatives + r")\b"),
                "func": func,
                "description": description,
                "category": category,
                "priority": priority,
                "risky": risky,
                "followup": followup,
                "name": func.__name__,
            })
            self.commands.sort(key=lambda c: -c.get("priority", 0))
            return func
        return decorator

    def get_all(self):
        return list(self.commands)


# Глобальный реестр — единственный на весь проект
registry = CommandRegistry()


# ============================================================
#  ШИНА СОБЫТИЙ
# ============================================================
_subscribers = []


def subscribe(callback):
    """Подписаться на события ядра.
    callback(source: str, text: str, response: str)"""
    if callback not in _subscribers:
        _subscribers.append(callback)


def unsubscribe(callback):
    if callback in _subscribers:
        _subscribers.remove(callback)


def emit_event(source: str, text: str, response: str):
    """Разослать событие всем подписчикам."""
    for cb in list(_subscribers):
        try:
            cb(source, text, response)
        except Exception as e:
            print(f"[emit_event] Ошибка в подписчике {cb}: {e}")


# Хуки выполненных команд (статистика и т.п.): cb(source, name, text, response).
# name — имя функции команды или "ai" для ответа GigaChat.
_command_hooks = []


def on_command(callback):
    if callback not in _command_hooks:
        _command_hooks.append(callback)


def _run_command_hooks(source, name, text, response):
    for cb in list(_command_hooks):
        try:
            cb(source, name, text, response)
        except Exception as e:
            print(f"[on_command] Ошибка в хуке {cb}: {e}")


# Откуда пришла текущая команда — нужно командам вроде «напомни»
# (напоминание из Telegram вернётся в Telegram).
_source = contextvars.ContextVar("kesha_source", default="app")


def current_source() -> str:
    return _source.get()


def announce(text: str, title: str = "Кеша", speak: bool = True, notify_user: bool = True):
    """Кеша говорит сама, без запроса: напоминание, будильник, таймер.
    Сообщение уходит в UI (источник "kesha"), во всплывашку Windows и в динамики."""
    text = localize(text)
    emit_event("kesha", "", text)
    if notify_user:
        try:
            from notify import notify
            notify(title, text)
        except Exception as e:
            print(f"[announce] уведомление: {e}")
    if speak:
        try:
            from voice import say
            say(text)
        except Exception as e:
            print(f"[announce] озвучка: {e}")


# ============================================================
#  AI HELPER (GigaChat)
# ============================================================
try:
    from help_manager import GigaChat
    _gig = GigaChat()
    AI_AVAILABLE = True
except Exception as e:
    print(f"[core] GigaChat недоступен: {e}")
    _gig = None
    AI_AVAILABLE = False


def gig_chat(gig, prompt: str) -> str:
    """Токен GigaChat живёт 30 минут, а help_manager берёт его один раз.
    Протух (401) — сбрасываем, chat() возьмёт новый, и пробуем ещё раз."""
    try:
        return gig.chat(prompt)
    except Exception as e:
        if "401" not in str(e) and "expired" not in str(e).lower():
            raise
        gig._token = None
        return gig.chat(prompt)

_CMD_REPLY = re.compile(r"^\s*CMD\s*:\s*(.+?)\s*$", re.I | re.S)
_ACT_REPLY = re.compile(r"^\s*ACT\s*:\s*(.+?)\s*$", re.I | re.S)    # задача для Клода
_ROBOT = re.compile(r"^(?!.*голос).*\bробот", re.I)    # про робота, но не «голос робота»


def _commands_hint() -> str:
    """Безопасные команды для GigaChat — только фразы (с описаниями модель путается
    и отвечает описанием): «- включи свет / включи лампу / зажги свет»."""
    lines = []
    for c in registry.commands:
        if c.get("risky"):
            continue
        lines.append("- " + " / ".join(c["patterns"][:3]))
    return "\n".join(lines)


_AI_RULES = (
    "Ниже фразы-команды, которые Кеша умеет выполнять. Если пользователь просит одну из них "
    "другими словами (перефразирование, сленг, опечатка), ответь ровно одной строкой: "
    "CMD: <фраза из списка> — добавь параметры пользователя (запрос, город, число), "
    "больше ничего не пиши. Если это вопрос или разговор, а не команда — просто ответь, без CMD. "
    "Фразу распознали по голосу: если она бессмысленная, обрывочная или непонятно, чего хотят, "
    "ответь ровно: Не понял.\n"
    "Если просят сделать что-то на компьютере (окна, программы, папки, настройки звука и экрана), "
    "а подходящей команды в списке нет — ответь ровно одной строкой: ACT: <задача полностью "
    "своими словами>.\n"
    "Примеры:\n"
    "«врубай что-нибудь послушать» -> CMD: включи музыку\n"
    "«сделай звук потише» -> CMD: тише\n"
    "«глянь, что там с погодой в Сочи» -> CMD: погода в сочи\n"
    "«какая столица Франции?» -> Париж.\n"
    "«выведи ватсап на передний план» -> ACT: выведи окно WhatsApp на передний план\n"
    "«пусть робот поедет вперёд» -> ACT: робот Raspbot: проехать немного вперёд\n"
)


def _build_prompt(text: str, context: str, with_commands: bool) -> str:
    parts = ["Ты голосовой помощник Кеша. Отвечай кратко и по делу. Без смайликов. "
             f"Ответ — одно короткое предложение, не длиннее {AI_MAX_WORDS} слов."]
    if settings.get("language") == "en":
        parts.append("Отвечай на английском языке.")
    if with_commands:
        parts.append(_AI_RULES + "Команды:\n" + _commands_hint())
    if context:
        parts.append("Предыдущий диалог:\n" + context)
    parts.append("Фраза пользователя: " + text)
    return "\n\n".join(parts)


def short_answer(answer: str, limit: int = None) -> str:
    """Голосом длинное слушать не хочется: не больше limit слов. Первое предложение,
    если оно влезает, иначе первые слова."""
    limit = limit or AI_MAX_WORDS
    words = answer.split()
    if len(words) <= limit:
        return answer
    first = re.split(r"(?<=[.!?])\s", answer, maxsplit=1)[0]
    if len(first.split()) <= limit:
        return first
    return " ".join(words[:limit]).rstrip(",;:—-") + "."


def ai_answer(question: str) -> str:
    """«Спроси …»: просто ответ ИИ, без поиска команд."""
    if not AI_AVAILABLE or _gig is None:
        return "ИИ сейчас недоступен."
    key = "ask:" + normalize(question)
    cached = ai_cache.get(key)
    if cached is None:
        try:
            cached = (gig_chat(_gig, _build_prompt(question, "", with_commands=False)) or "").strip()
        except Exception as e:
            print(f"[ai_answer] {e}")
            return "ИИ не ответил."
        for ch in '*%»`#$"':
            cached = cached.replace(ch, "")
        if cached:
            ai_cache.put(key, cached)
    return short_answer(cached) if cached else "ИИ не ответил."


def ai_ask(text: str, context: str = "") -> str:
    """Спросить GigaChat. Ответ вида «CMD: <команда>» значит, что фраза — команда
    (разбирает handle_command). Одинаковые вопросы берём из кэша (без контекста)."""
    if not AI_AVAILABLE or _gig is None:
        return "Не понял команду."
    key = "" if context else normalize(text)
    if key and settings.get("language") != "ru":
        key = f"{settings.get('language')}:{key}"
    cached = ai_cache.get(key)
    if cached is not None:
        return cached
    try:
        with_commands = len(text.split()) <= AI_COMMANDS_MAX_WORDS
        answer = gig_chat(_gig, _build_prompt(text, context, with_commands))
        answer = (answer or "").strip()
        if not answer:
            return "Не понял команду."
        if not _CMD_REPLY.match(answer):
            for ch in '*%»`#$"':
                answer = answer.replace(ch, "")
            answer = answer.strip()
        ai_cache.put(key, answer)
        return answer
    except Exception as e:
        print(f"[ai_ask] {e}")
        return "Не понял команду."


_LANG_NAMES = {"en": "английский"}


def translate(text: str, lang: str = "en") -> str:
    """Перевести ответ Кеши (GigaChat, с кэшем). Не вышло — вернуть как есть."""
    if not text or not AI_AVAILABLE or _gig is None:
        return text
    key = f"tr:{lang}:{text}"
    cached = ai_cache.get(key)
    if cached is not None:
        return cached
    try:
        answer = gig_chat(_gig, f"Переведи на {_LANG_NAMES.get(lang, lang)} язык. "
                           f"Ответь только переводом, без пояснений и кавычек: {text}")
        answer = (answer or "").strip().strip('"«»')
        if answer:
            ai_cache.put(key, answer)
            return answer
    except Exception as e:
        print(f"[translate] {e}")
    return text


def localize(response: str) -> str:
    """В английском режиме переводим русские ответы команд."""
    if settings.get("language") == "ru" or not response or has_latin(response):
        return response
    return translate(response, settings.get("language"))


# ============================================================
#  ХЕЛПЕРЫ
# ============================================================
def remove_wake_words(text: str) -> str:
    # «Кеша, запиши: ...» -> «запиши: ...»; знаки в конце не трогаем — их печатает «напечатай».
    # По целым словам: «очисти кэш» и «кешбэк» больше не портятся.
    from wake_text import strip_wake
    return strip_wake(text.lower())


def _matching(text: str, allow_risky: bool = True):
    """Команды, чей паттерн встречается в тексте, по убыванию приоритета."""
    for cmd in registry.commands:
        if cmd.get("risky") and not allow_risky:
            continue
        if cmd["regex"].search(text):
            yield cmd


def _exact(text: str, allow_risky: bool = True):
    """Выполнить первую подошедшую команду. -> (cmd, ответ) или None.
    Команда может вернуть None — «не моё», тогда пробуем следующую."""
    for cmd in _matching(text, allow_risky):
        try:
            response = cmd["func"](text)
        except Exception as e:
            print(f"[{cmd['name']}] Ошибка: {e}")
            continue
        if response is not None:
            return cmd, response
    return None


# управление компьютером без «Кеша», как у Алисы: «громче», «пауза», «дальше», «скролл вниз»
QUICK_CONTROL = {
    "volume_up", "volume_down", "set_volume", "mute", "unmute",
    "music_pause", "music_resume", "music_next", "music_prev",
    "click_left", "click_right", "double_click", "scroll_up", "scroll_down",
    "mouse_up", "mouse_down", "mouse_left", "mouse_right", "minimize_window",
}
QUICK_MAX_WORDS = 4


def quick_control(text: str):
    """Короткая фраза — только команда управления (± одно слово вроде «ну»/«кеш»).
    -> (имя, ответ) или None. Длинную речь (видео, разговор) не трогаем."""
    q = " ".join(re.sub(r"[^\w\s]", " ", remove_wake_words(text or "")).split())
    words = q.split()
    if not words or len(words) > QUICK_MAX_WORDS:
        return None
    for cmd in registry.commands:
        if cmd["name"] not in QUICK_CONTROL:
            continue
        m = cmd["regex"].search(q)
        if not m or len(words) > len(m.group(0).split()) + 1:
            continue
        try:
            resp = cmd["func"](q)
        except Exception as e:
            print(f"[{cmd['name']}] Ошибка: {e}")
            continue
        if resp is not None:
            klog.phrase("RUN", "voice", q, f"{cmd['name']} без «Кеша»")
            return cmd["name"], resp
    return None


def _understand(clean: str, source: str, sess):
    """Шаги 2–4: синонимы, follow-up, fuzzy. -> (cmd, ответ) или None."""
    norm = normalize(clean)
    if not norm or has_negation(norm):
        return None

    # follow-up: «а в питере»
    followup = sess.resolve_followup(norm)
    if followup:
        hit = _exact(followup, allow_risky=False)
        if hit:
            klog.phrase("FOLLOWUP", source, clean, f"{followup} -> {hit[0]['name']}")
            return hit

    if is_question(norm):
        # «какая пагода»: fuzzy только если паттерн начинается с того же вопросительного слова,
        # иначе «как дела у мамы» превратилось бы в команду
        m = fuzzy_find(norm, registry.commands)
        if m and normalize(m.pattern).split()[0] == norm.split()[0]:
            hit = _exact(m.rewritten, allow_risky=False)
            if hit:
                klog.phrase("FUZZY", source, clean, f"{m.pattern!r} {m.score:.2f} -> {hit[0]['name']}")
                return hit
        return None

    # синонимы: «вруби лампу»
    syn = apply_synonyms(norm)
    if syn != norm:
        hit = _exact(syn, allow_risky=False)
        if hit:
            klog.phrase("SYNONYM", source, clean, f"{syn} -> {hit[0]['name']}")
            return hit

    # fuzzy: «включи лапму»
    m = fuzzy_find(syn, registry.commands)
    if m:
        hit = _exact(m.rewritten, allow_risky=False)
        if hit:
            klog.phrase("FUZZY", source, clean,
                        f"{m.pattern!r} {m.score:.2f} -> {hit[0]['name']}")
            return hit
    return None


def _answer_as_command(answer: str):
    """GigaChat иногда забывает «CMD:» и отвечает самой фразой команды
    («Включи музыку», «узнай погоду | какая погода»). Если короткий ответ
    дословно равен фразе безопасной команды — считаем это командой."""
    if len(answer.split()) > 6:
        return None
    for piece in re.split(r"[|/;\n]", answer):
        phrase = normalize(piece)
        if not phrase:
            continue
        for cmd in registry.commands:
            if not cmd.get("risky") and any(normalize(p) == phrase for p in cmd["patterns"]):
                return phrase
    return None


def _ask_ai(clean: str, source: str, sess):
    """Шаг 5. -> (cmd или None, ответ)."""
    norm = normalize(clean)
    from features import claude_agent
    item = claude_agent.learned(norm)
    if item:                                   # Клод уже это делал — повторяем сами
        klog.phrase("LEARNED", source, clean, item["ps"][:70])
        return {"name": "learned"}, claude_agent.run_learned(item)
    if _ROBOT.search(norm):                    # робота умеет только Клод — GigaChat не спрашиваем
        return _ask_claude("робот Raspbot: " + clean, clean, source)
    ctx = sess.context() if session.looks_like_followup(norm) else ""
    answer = ai_ask(clean, context=ctx) if ctx else ai_ask(clean)

    act = _ACT_REPLY.match(answer)
    if act:
        return _ask_claude(act.group(1).strip(" \"'«»`"), clean, source)

    m = _CMD_REPLY.match(answer)
    rewritten = m.group(1).strip(" \"'«»`.").lower() if m else _answer_as_command(answer)
    if rewritten is None:
        klog.phrase("UNKNOWN", source, clean, "ответ: " + answer[:80])
        return None, short_answer(answer)

    hit = _exact(rewritten, allow_risky=False)
    if hit:
        klog.phrase("AI_CMD", source, clean, f"{rewritten!r} -> {hit[0]['name']}")
        return hit
    klog.phrase("UNKNOWN", source, clean, f"AI предложил {rewritten!r}, но команды нет")
    return None, "Не понял команду."


def _ask_claude(task: str, clean: str, source: str):
    """Готовой команды нет — задачу делает Клод в фоне, итог Кеша скажет сама."""
    from features import claude_agent
    if not claude_agent.ENABLED:
        klog.phrase("UNKNOWN", source, clean, f"ACT {task!r}, Клод выключен")
        return None, "Такого я пока не умею."
    if claude_agent.is_dangerous(task) or claude_agent.is_dangerous(clean):
        klog.phrase("UNKNOWN", source, clean, f"ACT {task!r} — опасно, Клоду не даю")
        return None, "Такое не доверю даже Клоду."

    def done(text):
        klog.phrase("CLAUDE", source, clean, text[:80])
        announce(short_answer(text, 20), title="Клод", speak=source == "voice")
        if source == "telegram":
            try:
                from features import messenger
                messenger.send_to_owners(text)
            except Exception as e:
                print(f"[claude] Telegram: {e}")

    if not claude_agent.run(task, clean, done):
        return {"name": "claude"}, "Клод ещё занят прошлой задачей."
    klog.phrase("AI_CMD", source, clean, f"ACT {task!r} -> claude")
    return {"name": "claude"}, "Сейчас сделаю."


def _ai_fix(clean: str, source: str, sess):
    """Фраза без «Кеша» в окне команд (сразу после команды), локально не поняли.
    GigaChat только исправляет её в команду («новая вкладочка» -> «новая вкладка»);
    свободный ответ не озвучиваем — это мог быть фон."""
    if not AI_FIX_COMMANDS or len(clean.split()) > AI_FIX_MAX_WORDS or not AI_AVAILABLE:
        klog.phrase("UNKNOWN", source, clean, "без слова «Кеша» — GigaChat не спрашиваю")
        return None
    norm = normalize(clean)
    ctx = sess.context() if session.looks_like_followup(norm) else ""
    answer = ai_ask(clean, context=ctx) if ctx else ai_ask(clean)
    m = _CMD_REPLY.match(answer)
    rewritten = m.group(1).strip(" \"'«»`.").lower() if m else _answer_as_command(answer)
    # исправление, а не выдумка: в команде должно остаться слово, похожее на сказанное
    # («вкл муззыку» -> «включи музыку» да; «ребята теай» -> «скролл вниз» — нет, это фон)
    if not rewritten or not _shares_word(norm, normalize(rewritten)):
        klog.phrase("UNKNOWN", source, clean, f"без «Кеша»: ИИ предложил {rewritten!r} — не похоже, не выполняю")
        return None
    hit = _exact(rewritten, allow_risky=False)
    if hit:
        klog.phrase("AI_FIX", source, clean, f"{rewritten!r} -> {hit[0]['name']}")
    return hit


def _shares_word(a: str, b: str) -> bool:
    from difflib import SequenceMatcher
    return any(SequenceMatcher(None, x, y).ratio() >= 0.6
               for x in a.split() if len(x) >= 3 for y in b.split() if len(y) >= 3)


# «и» / «потом» / «затем» между двумя командами: каждая часть должна сама быть командой
_SPLIT_RE = re.compile(r"\s*,?\s*\b(?:а потом|и потом|потом|затем|после этого|а ещё|а еще|и)\b\s*|\s*[,;]\s*")
NO_SPLIT = {"open_first_link", "add_note", "add_todo", "type_text", "send_message", "translate_free"}


def split_commands(clean: str) -> list:
    """«открой ютуб и найди котиков» -> ["открой ютуб", "найди котиков"]. Не делим, если
    хоть одна часть не команда («включи свет и музыку») или вся фраза — текст для команды
    («запиши: купить хлеб и молоко»)."""
    if not _SPLIT_RE.search(clean):
        return [clean]
    first = next(_matching(clean), None)
    if first is not None and first["name"] in NO_SPLIT:
        return [clean]
    parts = [p.strip(" ,.") for p in _SPLIT_RE.split(clean) if p and p.strip(" ,.")]
    if len(parts) < 2 or not all(next(_matching(p), None) is not None for p in parts):
        return [clean]
    return parts


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
# ---------- вопрос «да / нет» после команды («Открыть первую ссылку?») ----------
ASK_TTL = 20            # с: дольше ответ «да» уже не про этот вопрос
_YES = {"да", "давай", "ага", "угу", "конечно", "открой", "открывай", "да давай", "да открой",
        "давай открой", "можно", "ну давай", "да конечно", "yes", "ок да", "хочу"}
_NO = {"нет", "не", "неа", "не надо", "не нужно", "нет спасибо", "не открывай", "отмена",
       "не стоит", "нет не надо", "не хочу", "ну нет"}
_asked = {}             # источник -> (что сделать на «да», до какого времени ждём)


def ask_yes_no(on_yes, ttl=ASK_TTL):
    """Команда задала вопрос: следующий «да» вызовет on_yes(), «нет» ответит «Ок»."""
    _asked[current_source()] = (on_yes, time.time() + ttl)


def _answer_question(clean, source):
    pending = _asked.pop(source, None)          # любая следующая фраза закрывает вопрос
    if not pending or time.time() > pending[1]:
        return None
    reply = " ".join(clean.lower().replace("ё", "е").strip(" .,!?").split())
    if reply in _YES:
        token = _source.set(source)
        try:
            return pending[0]()
        finally:
            _source.reset(token)
    if reply in _NO:
        return "Ок"
    return None


def handle_command(text: str, source: str = "app", ai: bool = True) -> str:
    """
    Принимает команду от любого интерфейса.
    :param source: "app" | "telegram" | "alice" | "website" | "voice"
    :param ai: False — только локальные команды, без GigaChat (голос без слова «Кеша»:
               фоновая речь из телевизора не должна превращаться в команды). Не нашлось — "".
    """
    if not text or not text.strip():
        return ""

    clean = fix_mixed_script(remove_wake_words(text))
    answer = _answer_question(clean, source)
    if answer is not None:
        klog.phrase("RUN", source, clean, f"ответ на вопрос -> {answer[:70]}")
        emit_event(source, text, answer)
        return answer
    from features import robot
    answer = robot.followup(clean)              # «назад» сразу после «робот вперёд» — роботу
    if answer is not None:
        klog.phrase("RUN", source, clean, f"robot_followup -> {answer}")
        emit_event(source, text, answer)
        return answer
    parts = split_commands(clean)
    if len(parts) > 1:                  # «включи музыку и сделай громче»
        klog.phrase("MULTI", source, clean, " | ".join(parts))
        answers = [handle_command(p, source=source, ai=ai) for p in parts]
        return " ".join(a for a in answers if a)
    sess = session.get(source)
    token = _source.set(source)
    try:
        hit = _exact(clean) or _understand(clean, source, sess)
        if not hit and not ai:
            hit = _ai_fix(clean, source, sess)
            if not hit:
                return ""
        cmd, response = hit if hit else _ask_ai(clean, source, sess)
    finally:
        _source.reset(token)

    sess.remember(clean, response, cmd.get("followup") if cmd else None)
    if cmd:
        klog.phrase("RUN", source, clean, f"{cmd['name']} -> {(response or '')[:70]}")
    _run_command_hooks(source, cmd["name"] if cmd else "ai", clean, response)

    response = localize(response)
    emit_event(source, text, response)
    return response


# ============================================================
#  УТИЛИТЫ
# ============================================================
def list_commands():
    """Вывести все зарегистрированные команды."""
    if not registry.commands:
        print("[core] Реестр пуст. Подключи commands.py в main.py.")
        return
    print(f"\n[core] Зарегистрировано команд: {len(registry.commands)}")
    print("=" * 60)
    for cmd in registry.commands:
        patterns = ", ".join(cmd["patterns"])
        print(f"  [{cmd['category']:12}] {cmd['name']:20} ← {patterns}")
    print("=" * 60)


if __name__ == "__main__":
    print("Проверка core.py")
    print("AI доступен:", AI_AVAILABLE)

    def test_sub(source, text, response):
        print(f"  [event] {source}: '{text}' -> '{response}'")

    subscribe(test_sub)

    print("\nТест handle_command:")
    result = handle_command("привет", source="app")
    print(f"  Ответ: {result}")
