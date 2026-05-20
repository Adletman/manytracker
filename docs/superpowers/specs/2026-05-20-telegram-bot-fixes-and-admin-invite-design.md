# Design: починка Telegram-бота + админ-генерация кодов привязки

**Дата:** 2026-05-20
**Проект:** ManyTracker (Wedrink)
**Автор:** Adlet Kartov + Claude

## Цели

1. **Fix-1.** Восстановить работу Telegram-бота на Railway (сейчас не отвечает).
2. **Fix-2.** Починить кнопку «Расход» (нажатие не вызывает реакции).
3. **Feature.** Дать админу в Django admin (`/admin/`) возможность одним кликом сгенерировать одноразовый 6-значный код привязки для конкретного сотрудника, копируя в буфер обмена готовый текст-инструкцию (ссылка + код + пошаговка). После привязки бот выдаёт сотруднику короткую памятку по кнопкам меню.

Замена существующего флоу (сотрудник сам в `/cabinet/profile/` нажимает «Привязать Telegram») не предполагается — он остаётся как fallback.

## Корневая причина Fix-1

В `Procfile` для Railway указан только процесс `web:` (gunicorn). Отдельного worker-процесса для бота нет. Railway по умолчанию читает Procfile/Dockerfile, не `docker-compose.yml` (в котором бот описан как сервис). Следовательно, polling-процесс никогда не запускался — отсюда полное молчание бота.

## Корневая причина Fix-2 (гипотезы)

«Расход» не реагирует. Гипотезы по убыванию вероятности:

1. **Бот не запущен** — устраняется Fix-1.
2. **Тихое исключение в хэндлере** — например, в `_get_category_keyboard()` (`bot/handlers/add_expense.py:25`) при пустой таблице `ExpenseCategory` или недоступной БД. У бота нет `application.add_error_handler`, поэтому исключения внутри `ConversationHandler` поглощаются. Лечится добавлением глобального error handler с логированием и информативным ответом юзеру.
3. **Залипший state в памяти** — не наш кейс, persistence не используется, рестарт сбрасывает.

Финальный фикс зависит от того, воспроизведётся ли проблема после Fix-1. В любом случае добавляем error handler — это даёт логи и UX-обратную связь на будущее.

## Архитектура фичи (admin invite)

```
Admin /admin/accounts/user/        Backend                        Telegram Bot
─────────────────────────────      ─────────────────────────      ─────────────────
[список сотрудников]
  ↓ click "Сген. код TG"
  AJAX POST /admin/accounts/   →   view generate_telegram_code:
    user/<id>/gen-tg-code/         - @staff_member_required
                                   - @require_POST
                                   - retry-loop генерации
                                     уникального 6-зн. кода
                                   - save user.telegram_link_code,
                                          expires_at = now+10min
                                   - return JSON {code, copy_text}
  ↓ JS обрабатывает JSON
  navigator.clipboard.writeText(
    copy_text)
  toast "Скопировано: 123456"
  кнопка → inline-индикатор кода
  ↓
[Админ вставляет в WA/TG чат
 сотруднику]

                                                                   Сотрудник:
                                                              ←    /start 123456
                                                                   (или ссылка
                                                                   t.me/bot?start=…)

                                   bot.handlers.start.start_command:
                                   - link_user_by_code(123456, tg_id)
                                   - User.objects.get(code=,
                                       expires_at__gte=now)
                                   - сохранить telegram_id
                                   - очистить code + expires_at
                                                                   →
                                                              →    WELCOME_AFTER_LINK
                                                                   (приветствие +
                                                                    памятка)
                                                                   + main_menu_keyboard
```

## Компоненты и изменения по файлам

### 1. `Procfile`

Добавить строку:
```
bot: python manage.py run_bot
```

### 2. Railway

В том же проекте Railway создать **второй сервис** из этого же репо. Settings → Start Command: `python manage.py run_bot`. Скопировать те же env-переменные (DATABASE_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME, и т.д.). Procfile c несколькими записями Railway не запустит — нужны два независимых сервиса (web + worker).

### 3. `config/settings.py`

```python
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "")
```

### 4. `.env.example`

Добавить:
```
TELEGRAM_BOT_USERNAME=WedrinkExpenseBot
```
(без `@`).

### 5. `accounts/admin_views.py` (новый файл)

```python
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
```

### 6. `accounts/admin.py`

В `UserAdmin`:
- расширить `list_display`: добавить `telegram_status`, `telegram_action`
- методы `telegram_status` (привязан/—) и `telegram_action` (HTML-кнопка с `data-user-id`)
- `get_urls()` регистрирует view по path `<int:user_id>/gen-tg-code/`
- `class Media` подключает `static/admin/js/telegram_code.js`

### 7. `static/admin/js/telegram_code.js` (новый, ~40 строк)

- Делегированный listener на `click` по `.btn-gen-tg-code`
- Берёт CSRF из cookie `csrftoken`
- `fetch(url, {method:"POST", headers:{"X-CSRFToken": token}, credentials:"same-origin"})`
- При успехе: `navigator.clipboard.writeText(json.copy_text)` → toast «Скопировано: код 123456 (действует 10 мин)»
- При ошибке: alert с сообщением, кнопка возвращается в исходное
- Обновляет содержимое кнопки → показывает текущий код inline (до перезагрузки страницы)

### 8. `bot/handlers/start.py`

- Вынести в константу:
  ```python
  WELCOME_AFTER_LINK = (
      "Привязано! Добро пожаловать, {name}!\n\n"
      "Как пользоваться:\n"
      "• Баланс — твой остаток\n"
      "• Расход — добавить трату (фото чека по желанию)\n"
      "• Приход — пополнение (с комментарием)\n"
      "• История — последние 10 операций\n\n"
      "Если запутался — отправь /start"
  )
  ```
- Использовать в `start_command` и `text_code_handler` после успешной привязки.

### 9. `bot/management/commands/run_bot.py`

Добавить error handler:
```python
async def error_handler(update, context):
    logger.exception("Bot error", exc_info=context.error)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text("Произошла ошибка. Попробуйте /start")
        except Exception:
            pass

app.add_error_handler(error_handler)
```

### 10. Тесты

**`accounts/tests.py`** (или `accounts/tests/test_admin_invite.py`):
- `test_generate_telegram_code_view_requires_staff` — анонимный POST → 302/403
- `test_generate_telegram_code_view_success` — staff POST → 200, JSON содержит `code` (6 цифр), `copy_text` с ссылкой и кодом; в БД у пользователя сохранены `telegram_link_code` и `telegram_link_code_expires_at`
- `test_generate_telegram_code_view_collision_retry` — мок `secrets.randbelow` возвращает существующий код первым, новый вторым → ассертим что сохранился второй
- `test_generate_telegram_code_view_get_not_allowed` — GET → 405

**`bot/tests.py`** (или `bot/tests/test_link_flow.py`):
- `test_link_user_by_code_success` — настраиваем юзера с активным кодом → link сохраняет telegram_id, очищает код
- `test_link_user_by_code_expired` — expires_at в прошлом → None, telegram_id не меняется
- `test_link_user_by_code_invalid` — несуществующий код → None

Запуск: `POSTGRES_HOST=localhost pytest -v accounts/ bot/`.

## Обработка ошибок

- **Frontend (JS):** не-2xx ответ → `alert("Ошибка: " + статус)`, кнопка восстанавливается.
- **Backend view:** `_generate_unique_code` после 10 коллизий бросает `RuntimeError` → Django вернёт 500; коллизия двух активных 6-зн. кодов из ~1M пула при ~десятках сотрудников — практически невозможна.
- **Бот:** error handler логирует и отвечает юзеру; `TELEGRAM_BOT_TOKEN` отсутствует → `run_bot` выходит со stderr (уже реализовано в `run_bot.py:13`).

## План e2e-тестирования (вручную, после деплоя Fix-1)

1. Локально: `docker compose up -d postgres web bot`, проверить логи `bot`.
2. `/admin/` → залогиниться → создать тест-сотрудника → клик «Сген. код» → проверить toast и буфер.
3. Содержимое буфера должно открывать рабочую ссылку `https://t.me/<bot>?start=123456`.
4. Из другого Telegram-аккаунта перейти по ссылке → должно показать приветствие с памяткой и меню.
5. **Баланс** → ответ «Ваш баланс: 0 ₸».
6. **Расход** → категории → выбрать → сумма → /skip → /skip → подтвердить → ✓. Если зависает — смотрим логи (теперь они есть благодаря error_handler) и фиксим конкретное исключение.
7. **Приход** → сумма → комментарий → подтвердить → ✓.
8. **История** → видим обе операции.
9. В БД у тестового юзера: `telegram_id` сохранён, `telegram_link_code` и `telegram_link_code_expires_at` обнулены.

## YAGNI / скоуп

- **НЕ** делаем новую модель `TelegramInvite` с историей приглашений (избыточно).
- **НЕ** меняем формат кода (6 цифр / 10 минут оставляем — совместимо с существующим flow в `/cabinet/profile/`).
- **НЕ** делаем отдельную страницу-modal — кнопка в changelist + clipboard достаточно.
- **НЕ** добавляем video/screenshot в памятку бота — короткий текст по кнопкам.

## Открытые вопросы (на момент написания дизайна)

1. **Railway**: есть ли уже worker-сервис для бота? Пользователь не уверен. Проверим вместе перед Fix-1.
2. **Имя бота (`TELEGRAM_BOT_USERNAME`)**: уточним при настройке env-переменной.
