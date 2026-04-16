from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.handlers.start import get_user_by_telegram_id
from expenses.services.balance import get_balance as _get_balance


@sync_to_async
def _balance(user):
    return _get_balance(user)


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт: /start")
        return
    balance = await _balance(user)
    sign = "+" if balance >= 0 else ""
    await update.message.reply_text(f"Ваш баланс: {sign}{balance} ₸")


def get_balance_handler():
    return MessageHandler(filters.Regex("^Баланс$"), balance_handler)
