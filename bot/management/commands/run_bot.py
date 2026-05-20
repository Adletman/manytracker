import logging
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


async def error_handler(update, context):
    logger.exception("Bot error", exc_info=context.error)
    if update and getattr(update, "effective_message", None):
        try:
            await update.effective_message.reply_text(
                "Произошла ошибка. Попробуйте /start"
            )
        except Exception:
            pass


class Command(BaseCommand):
    help = "Run the Telegram bot"

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stderr.write("TELEGRAM_BOT_TOKEN is not set")
            return

        from telegram.ext import ApplicationBuilder, MessageHandler, filters
        from bot.handlers.start import get_start_handler, text_code_handler
        from bot.handlers.menu import get_menu_handler
        from bot.handlers.balance import get_balance_handler
        from bot.handlers.add_expense import get_expense_handler
        from bot.handlers.add_topup import get_topup_handler
        from bot.handlers.history import get_history_handler

        app = ApplicationBuilder().token(token).build()

        app.add_handler(get_start_handler())
        app.add_handler(get_expense_handler())
        app.add_handler(get_topup_handler())
        app.add_handler(get_balance_handler())
        app.add_handler(get_history_handler())
        app.add_handler(MessageHandler(
            filters.Regex(r"^\d{6}$") & ~filters.COMMAND,
            text_code_handler,
        ))
        app.add_handler(get_menu_handler())
        app.add_error_handler(error_handler)

        self.stdout.write("Bot starting...")
        app.run_polling(drop_pending_updates=True)
