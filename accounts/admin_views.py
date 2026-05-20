import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import User


def _generate_unique_code():
    for _ in range(10):
        code = f"{secrets.randbelow(1_000_000):06d}"
        if not User.objects.filter(telegram_link_code=code).exists():
            return code
    raise RuntimeError("Не удалось сгенерировать уникальный код после 10 попыток")


@staff_member_required
@require_POST
def generate_telegram_code(request, user_id):
    user = get_object_or_404(User, id=user_id, is_active=True)
    code = _generate_unique_code()
    user.telegram_link_code = code
    user.telegram_link_code_expires_at = timezone.now() + timedelta(minutes=10)
    user.save(update_fields=["telegram_link_code", "telegram_link_code_expires_at"])

    bot = settings.TELEGRAM_BOT_USERNAME or "your_bot"
    copy_text = (
        f"Привет! Подключаем тебя к учёту расходов Wedrink.\n\n"
        f"1. Открой бота: https://t.me/{bot}\n"
        f"2. Нажми «Запустить» (Start)\n"
        f"3. Отправь этот код: {code}\n"
        f"   Или сразу перейди по ссылке:\n"
        f"   https://t.me/{bot}?start={code}\n\n"
        f"Код действует 10 минут."
    )
    return JsonResponse({"code": code, "copy_text": copy_text})
