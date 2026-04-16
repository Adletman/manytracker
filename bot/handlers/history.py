from itertools import chain

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.handlers.start import get_user_by_telegram_id
from expenses.models import Expense, Topup


@sync_to_async
def _get_operations(user):
    expenses = list(
        Expense.objects.filter(user=user, is_deleted=False)
        .select_related("category").order_by("-date", "-created_at")[:10]
    )
    topups = list(Topup.objects.filter(user=user).order_by("-date", "-created_at")[:10])

    operations = sorted(
        chain(
            [{"type": "expense", "date": e.date, "label": e.category_display(),
              "amount": e.amount} for e in expenses],
            [{"type": "topup", "date": t.date, "label": t.comment or "Пополнение",
              "amount": t.amount} for t in topups],
        ),
        key=lambda x: x["date"],
        reverse=True,
    )[:10]
    return operations


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт: /start")
        return

    operations = await _get_operations(user)

    if not operations:
        await update.message.reply_text("История пуста.")
        return

    lines = []
    for op in operations:
        if op["type"] == "expense":
            lines.append(f"↓ −{op['amount']} ₸  {op['label']}  ({op['date'].strftime('%d.%m')})")
        else:
            lines.append(f"↑ +{op['amount']} ₸  {op['label']}  ({op['date'].strftime('%d.%m')})")

    await update.message.reply_text("\n".join(lines))


def get_history_handler():
    return MessageHandler(filters.Regex("^История$"), history_handler)
