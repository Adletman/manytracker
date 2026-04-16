from datetime import date
from decimal import Decimal, InvalidOperation

from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.handlers.start import get_user_by_telegram_id
from bot.keyboards import main_menu_keyboard
from expenses.services.balance import get_balance as _get_balance_sync
from expenses.services.topups import create_topup as _create_topup_sync

AMOUNT, COMMENT, CONFIRM = range(3)


@sync_to_async
def _get_balance(user):
    return _get_balance_sync(user)


@sync_to_async
def _create_topup(**kwargs):
    return _create_topup_sync(**kwargs)


async def topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт: /start")
        return ConversationHandler.END
    context.user_data["topup_user"] = user
    await update.message.reply_text("Введите сумму прихода (₸):")
    return AMOUNT


async def amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".").replace(" ", "")
    try:
        amount = Decimal(text)
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await update.message.reply_text("Введите корректную сумму больше нуля:")
        return AMOUNT
    context.user_data["topup_amount"] = amount
    await update.message.reply_text("Комментарий (от кого / за что):")
    return COMMENT


async def comment_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text.strip()
    if not comment:
        await update.message.reply_text("Комментарий обязателен. Напишите от кого / за что:")
        return COMMENT
    context.user_data["topup_comment"] = comment

    amount = context.user_data["topup_amount"]
    text = f"Приход: +{amount} ₸\nКомментарий: {comment}\n\nПодтвердить?"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Подтвердить", callback_data="topup_yes"),
         InlineKeyboardButton("Отмена", callback_data="topup_no")],
    ])
    await update.message.reply_text(text, reply_markup=kb)
    return CONFIRM


async def confirm_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    user = ud["topup_user"]
    try:
        topup = await _create_topup(
            created_by=user, user=user,
            amount=ud["topup_amount"],
            topup_date=date.today(),
            comment=ud["topup_comment"],
            source="employee",
        )
    except Exception as e:
        await query.edit_message_text(f"Ошибка: {e}")
        return ConversationHandler.END

    balance = await _get_balance(user)
    await query.edit_message_text(
        f"✓ Приход: +{topup.amount} ₸\nБаланс: {balance} ₸",
    )
    return ConversationHandler.END


async def confirm_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Отменено.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def get_topup_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Приход$"), topup_start)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_entered)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment_entered)],
            CONFIRM: [CallbackQueryHandler(confirm_yes, pattern="^topup_yes$"),
                       CallbackQueryHandler(confirm_no, pattern="^topup_no$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
