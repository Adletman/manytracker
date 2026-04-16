from django.contrib.auth import get_user_model
from django.utils import timezone
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.keyboards import main_menu_keyboard

User = get_user_model()


def get_user_by_telegram_id(telegram_id: int):
    try:
        return User.objects.get(telegram_id=telegram_id, is_active=True)
    except User.DoesNotExist:
        return None


def link_user_by_code(code: str, telegram_id: int):
    now = timezone.now()
    try:
        user = User.objects.get(
            telegram_link_code=code,
            telegram_link_code_expires_at__gte=now,
        )
    except User.DoesNotExist:
        return None
    user.telegram_id = telegram_id
    user.telegram_link_code = None
    user.telegram_link_code_expires_at = None
    user.save(update_fields=["telegram_id", "telegram_link_code", "telegram_link_code_expires_at"])
    return user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id

    existing = get_user_by_telegram_id(telegram_id)
    if existing:
        await update.message.reply_text(
            f"Привет, {existing.full_name or existing.username}!",
            reply_markup=main_menu_keyboard(),
        )
        return

    text = update.message.text or ""
    parts = text.strip().split()
    code = parts[1] if len(parts) > 1 else None

    if not code:
        await update.message.reply_text(
            "Введите код привязки из веб-кабинета (Профиль → Привязать Telegram):"
        )
        return

    user = link_user_by_code(code, telegram_id)
    if user:
        await update.message.reply_text(
            f"Привязано! Добро пожаловать, {user.full_name or user.username}!",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.message.reply_text("Код неверный или истёк. Попробуйте получить новый в веб-кабинете.")


async def text_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    if get_user_by_telegram_id(telegram_id):
        return

    code = (update.message.text or "").strip()
    if not code.isdigit() or len(code) != 6:
        await update.message.reply_text("Введите 6-значный код из веб-кабинета.")
        return

    user = link_user_by_code(code, telegram_id)
    if user:
        await update.message.reply_text(
            f"Привязано! Добро пожаловать, {user.full_name or user.username}!",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.message.reply_text("Код неверный или истёк.")


def get_start_handler():
    return CommandHandler("start", start_command)
