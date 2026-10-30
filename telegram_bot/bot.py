"""Telegram-бот Кеша."""
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

from core import handle_command
from config import TELEGRAM_TOKEN, TELEGRAM_ALLOWED_IDS, ICON_PATH

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)   # иначе в лог попадает URL с токеном
log = logging.getLogger(__name__)


def allowed(func):
    """Пускает только пользователей из TELEGRAM_ALLOWED_IDS; остальным показывает их id."""
    async def wrapper(u: Update, c: ContextTypes.DEFAULT_TYPE):
        user = u.effective_user
        uid = str(user.id) if user else ""
        if user:
            try:   # для «напиши маме в телеграм»: бот помнит, кто ему писал
                from features import messenger
                messenger.remember_user(user.id, user.first_name, user.username)
            except Exception as e:
                log.warning("не удалось запомнить пользователя: %s", e)
        if uid not in TELEGRAM_ALLOWED_IDS:
            log.warning("Отказано: user_id=%s", uid)
            if u.message:
                await u.message.reply_text(f"Доступ запрещён. Ваш id: {uid}")
            return
        return await func(u, c)
    return wrapper


@allowed
async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    from core import registry
    cats = {}
    for cmd in registry.commands:
        cats.setdefault(cmd["category"], []).append(cmd["description"])
    txt = "Кеша готов.\n\n"
    for cat, items in cats.items():
        txt += "*" + cat + "*\n"
        for it in items[:8]:
            txt += "  - " + it + "\n"
        txt += "\n"
    try:
        with open(ICON_PATH, "rb") as f:
            await u.message.reply_photo(f, caption=txt, parse_mode="Markdown")
    except Exception:
        await u.message.reply_text(txt)


@allowed
async def cmd_say(u: Update, c: ContextTypes.DEFAULT_TYPE):
    text = u.message.text.replace("/say", "").strip()
    if not text:
        await u.message.reply_text("Что сказать?")
        return
    try:
        from voice import say
        say(text, force=True)   # даже в тихом режиме — просили явно
        await u.message.reply_text("Озвучил: " + text)
    except Exception as e:
        await u.message.reply_text("Ошибка TTS: " + str(e))


@allowed
async def on_message(u: Update, c: ContextTypes.DEFAULT_TYPE):
    text = (u.message.text or "").strip()
    if not text:
        return
    response = await asyncio.to_thread(handle_command, text, "telegram")
    await u.message.reply_text(response or "...")


_conflict_warned = False

CONFLICT_HINT = ("Telegram: Conflict — этот же токен опрашивает ещё одна программа "
                 "(вторая копия Кеши на другом ПК/сервере, старый скрипт, хостинг). Работает только одна. "
                 "Закрой другую копию или выпусти новый токен: @BotFather → /revoke → впиши его в .env.")


async def on_error(u: object, c: ContextTypes.DEFAULT_TYPE):
    """Conflict — не авария: пишем понятную подсказку один раз, а не трейсбек каждые пару секунд."""
    global _conflict_warned
    from telegram.error import Conflict
    if isinstance(c.error, Conflict):
        if not _conflict_warned:
            _conflict_warned = True
            log.error(CONFLICT_HINT)
        return
    log.error("Ошибка Telegram-бота: %s", c.error, exc_info=c.error)


def start_bot():
    # Фикс event loop для потоков
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    if not TELEGRAM_ALLOWED_IDS:
        log.warning("TELEGRAM_ALLOWED_IDS пуст — бот никому не отвечает. "
                    "Напишите боту, он покажет ваш id, и впишите его в .env")
    log.info("Запуск Telegram-бота Кеша...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("say", cmd_say))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_error_handler(on_error)
    log.info("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    start_bot()
