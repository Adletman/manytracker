from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.handlers.start import get_user_by_telegram_id
from bot.keyboards import main_menu_keyboard


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт. Отправьте /start")
        return
    await update.message.reply_text(
        "Используйте меню ниже",
        reply_markup=main_menu_keyboard(),
    )


def get_menu_handler():
    return MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command)
