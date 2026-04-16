from datetime import date
from decimal import Decimal, InvalidOperation

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
from expenses.models import ExpenseCategory
from expenses.services.balance import get_balance
from expenses.services.expenses import NegativeBalanceError, create_expense

CATEGORY, CUSTOM_NAME, AMOUNT, COMMENT, FILE, CONFIRM = range(6)


def _category_keyboard():
    cats = list(ExpenseCategory.objects.filter(is_active=True).order_by("sort_order", "name"))
    buttons = [[InlineKeyboardButton(c.name, callback_data=f"cat_{c.id}")] for c in cats]
    buttons.append([InlineKeyboardButton("Другое", callback_data="cat_other")])
    return InlineKeyboardMarkup(buttons)


async def expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт: /start")
        return ConversationHandler.END
    context.user_data["expense_user"] = user
    await update.message.reply_text("Выберите категорию:", reply_markup=_category_keyboard())
    return CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "cat_other":
        context.user_data["expense_category"] = None
        await query.edit_message_text("Введите название категории:")
        return CUSTOM_NAME
    cat_id = int(data.replace("cat_", ""))
    try:
        cat = ExpenseCategory.objects.get(id=cat_id)
    except ExpenseCategory.DoesNotExist:
        await query.edit_message_text("Категория не найдена.")
        return ConversationHandler.END
    context.user_data["expense_category"] = cat
    context.user_data["expense_custom_name"] = ""
    await query.edit_message_text(f"Категория: {cat.name}\nВведите сумму (₸):")
    return AMOUNT


async def custom_name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Введите название:")
        return CUSTOM_NAME
    context.user_data["expense_custom_name"] = name
    await update.message.reply_text(f"Категория: {name}\nВведите сумму (₸):")
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
    context.user_data["expense_amount"] = amount
    await update.message.reply_text("Комментарий (или /skip):")
    return COMMENT


async def comment_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_comment"] = update.message.text.strip()
    await update.message.reply_text("Отправьте фото или документ чека (или /skip):")
    return FILE


async def comment_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_comment"] = ""
    await update.message.reply_text("Отправьте фото или документ чека (или /skip):")
    return FILE


async def file_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_file"] = True
    return await _show_confirm(update, context)


async def file_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_file"] = None
    return await _show_confirm(update, context)


async def _show_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    cat = ud.get("expense_category")
    cat_name = cat.name if cat else ud.get("expense_custom_name", "")
    amount = ud["expense_amount"]
    user = ud["expense_user"]
    balance = get_balance(user)
    projected = balance - amount

    text = f"Расход: {cat_name}\nСумма: {amount} ₸"
    if projected < 0:
        text += f"\n⚠️ Баланс станет {projected} ₸"
    text += "\n\nПодтвердить?"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Подтвердить", callback_data="exp_yes"),
         InlineKeyboardButton("Отмена", callback_data="exp_no")],
    ])
    await update.message.reply_text(text, reply_markup=kb)
    return CONFIRM


async def confirm_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    user = ud["expense_user"]
    try:
        expense = create_expense(
            user=user,
            category=ud.get("expense_category"),
            custom_name=ud.get("expense_custom_name", ""),
            amount=ud["expense_amount"],
            expense_date=date.today(),
            comment=ud.get("expense_comment", ""),
            created_via="telegram",
            allow_negative=True,
        )
    except Exception as e:
        await query.edit_message_text(f"Ошибка: {e}")
        return ConversationHandler.END

    balance = get_balance(user)
    await query.edit_message_text(
        f"✓ Расход: −{expense.amount} ₸ ({expense.category_display()})\nБаланс: {balance} ₸",
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


def get_expense_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Расход$"), expense_start)],
        states={
            CATEGORY: [CallbackQueryHandler(category_chosen)],
            CUSTOM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_name_entered)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_entered)],
            COMMENT: [
                CommandHandler("skip", comment_skip),
                MessageHandler(filters.TEXT & ~filters.COMMAND, comment_entered),
            ],
            FILE: [
                CommandHandler("skip", file_skip),
                MessageHandler(filters.Document.ALL | filters.PHOTO, file_received),
            ],
            CONFIRM: [CallbackQueryHandler(confirm_yes, pattern="^exp_yes$"),
                       CallbackQueryHandler(confirm_no, pattern="^exp_no$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
