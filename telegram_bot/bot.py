"""Telegram-бот Кеша."""
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

from core import handle_command
from config import TELEGRAM_TOKEN, ICON_PATH

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


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


async def cmd_say(u: Update, c: ContextTypes.DEFAULT_TYPE):
    text = u.message.text.replace("/say", "").strip()
    if not text:
        await u.message.reply_text("Что сказать?")
        return
    try:
        from voice import say
        say(text)
        await u.message.reply_text("Озвучил: " + text)
    except Exception as e:
        await u.message.reply_text("Ошибка TTS: " + str(e))


async def on_message(u: Update, c: ContextTypes.DEFAULT_TYPE):
    text = (u.message.text or "").strip()
    if not text:
        return
    response = handle_command(text, source="telegram")
    await u.message.reply_text(response or "...")


def start_bot():
    # Фикс event loop для потоков
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    log.info("Запуск Telegram-бота Кеша...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("say", cmd_say))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    log.info("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    start_bot()
