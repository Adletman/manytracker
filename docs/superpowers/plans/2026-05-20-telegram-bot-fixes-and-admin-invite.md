# Telegram Bot Fixes + Admin Invite Codes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Восстановить работу Telegram-бота (запуск + кнопка «Расход») и добавить в Django admin one-click генерацию 6-значного кода привязки с автоматическим копированием инструкции в буфер обмена.

**Architecture:**
- Бот запускается как отдельный worker-сервис на Railway через дополнительную строку в `Procfile`.
- В `bot/management/commands/run_bot.py` добавляется глобальный error handler — это и фикс «тихих» падений «Расход», и инфраструктура на будущее.
- Админ-генерация: AJAX-эндпоинт в `accounts/admin_views.py`, JS-обработчик в `static/admin/js/telegram_code.js`, кнопка через `list_display` в `UserAdmin`. Текст инструкции собирается на сервере с использованием `TELEGRAM_BOT_USERNAME` из env.

**Tech Stack:** Django 5.0, python-telegram-bot 21.5, pytest-django, factory_boy, Railway.

**Spec:** `docs/superpowers/specs/2026-05-20-telegram-bot-fixes-and-admin-invite-design.md`

---

## File Map

**Создать:**
- `accounts/admin_views.py` — view `generate_telegram_code` + helper `_generate_unique_code`
- `static/admin/js/telegram_code.js` — AJAX + clipboard + toast
- `tests/test_admin_invite.py` — тесты view + UI кнопки

**Изменить:**
- `Procfile` — добавить `bot:` процесс
- `config/settings.py` — добавить `TELEGRAM_BOT_USERNAME`
- `.env.example` — добавить переменную
- `bot/management/commands/run_bot.py` — добавить error handler
- `bot/handlers/start.py` — вынести `WELCOME_AFTER_LINK` константу, использовать в обоих сценариях привязки
- `accounts/admin.py` — расширить `UserAdmin` (list_display, get_urls, Media)
- `tests/test_bot_start.py` — добавить тест на текст приветствия после link

**Не меняем:** модели (поля `telegram_link_code`, `telegram_link_code_expires_at` уже есть), миграции, `expenses/`, остальные хэндлеры бота.

---

## Task 1: Procfile — добавить bot worker

**Files:**
- Modify: `Procfile`

- [ ] **Step 1: Открыть `Procfile`, посмотреть текущее содержимое**

Текущий:
```
web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py ensure_superuser && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
```

- [ ] **Step 2: Добавить вторую строку**

Новое содержимое:
```
web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py ensure_superuser && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
bot: python manage.py run_bot
```

- [ ] **Step 3: Commit**

```bash
git add Procfile
git commit -m "fix(deploy): add bot worker process to Procfile"
```

**Заметка:** На Railway этот Procfile с двумя записями не запустит автоматически второй процесс — нужно вручную создать второй сервис в том же проекте Railway (см. Task 8).

---

## Task 2: Bot error handler в run_bot

**Files:**
- Modify: `bot/management/commands/run_bot.py`

**Why:** Сейчас исключения внутри ConversationHandler/CallbackQuery поглощаются молча — юзер видит «ничего не происходит» (кейс кнопки «Расход»). Глобальный error_handler даёт логи и обратную связь юзеру.

- [ ] **Step 1: Открыть `bot/management/commands/run_bot.py`**

Текущая логика (для контекста):
```python
import logging
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Telegram bot"

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stderr.write("TELEGRAM_BOT_TOKEN is not set")
            return

        from telegram.ext import ApplicationBuilder, MessageHandler, filters
        from bot.handlers.start import get_start_handler, text_code_handler
        # ... остальные импорты
        app = ApplicationBuilder().token(token).build()
        app.add_handler(get_start_handler())
        # ... остальные add_handler
        self.stdout.write("Bot starting...")
        app.run_polling(drop_pending_updates=True)
```

- [ ] **Step 2: Добавить error_handler и подключить его перед `run_polling`**

Финальный файл:
```python
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
```

- [ ] **Step 3: Smoke-проверка (опционально, требует TELEGRAM_BOT_TOKEN локально)**

Локально:
```bash
POSTGRES_HOST=localhost TELEGRAM_BOT_TOKEN=<тестовый> python manage.py run_bot
```
Ожидается строка `Bot starting...` без traceback. Прерви Ctrl+C.

- [ ] **Step 4: Commit**

```bash
git add bot/management/commands/run_bot.py
git commit -m "fix(bot): add global error handler with logging and user feedback"
```

---

## Task 3: Setting TELEGRAM_BOT_USERNAME

**Files:**
- Modify: `config/settings.py`
- Modify: `.env.example`

- [ ] **Step 1: Добавить переменную в settings**

В `config/settings.py` рядом с `TELEGRAM_BOT_TOKEN` (строка 128) добавить ниже:
```python
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "")
```

- [ ] **Step 2: Добавить в `.env.example`**

В конец файла:
```
TELEGRAM_BOT_USERNAME=WedrinkExpenseBot
```

- [ ] **Step 3: Commit**

```bash
git add config/settings.py .env.example
git commit -m "feat(config): add TELEGRAM_BOT_USERNAME env var for invite links"
```

---

## Task 4: Welcome message constant + tests

**Files:**
- Modify: `bot/handlers/start.py`
- Modify: `tests/test_bot_start.py`

**Why TDD here:** мы хотим гарантировать что после link юзер видит памятку — это поведение, которое легко регрессирует при будущих рефакторингах.

- [ ] **Step 1: Открыть `tests/test_bot_start.py`, добавить failing-тест на текст приветствия**

В конец файла добавить:
```python
from bot.handlers.start import WELCOME_AFTER_LINK


def test_welcome_text_contains_menu_hints():
    text = WELCOME_AFTER_LINK.format(name="Alice")
    assert "Alice" in text
    assert "Баланс" in text
    assert "Расход" in text
    assert "Приход" in text
    assert "История" in text
```

- [ ] **Step 2: Запустить тест — должен упасть на импорте**

```bash
POSTGRES_HOST=localhost pytest tests/test_bot_start.py::test_welcome_text_contains_menu_hints -v
```
Ожидается: FAIL — `ImportError: cannot import name 'WELCOME_AFTER_LINK'`.

- [ ] **Step 3: Добавить константу в `bot/handlers/start.py`**

После импортов (после строки `User = get_user_model()`) добавить:
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

- [ ] **Step 4: Заменить два места отправки приветствия на константу**

В `start_command` строки 63-67:
```python
    user = await link_user_by_code(code, telegram_id)
    if user:
        await update.message.reply_text(
            f"Привязано! Добро пожаловать, {user.full_name or user.username}!",
            reply_markup=main_menu_keyboard(),
        )
```
Заменить на:
```python
    user = await link_user_by_code(code, telegram_id)
    if user:
        await update.message.reply_text(
            WELCOME_AFTER_LINK.format(name=user.full_name or user.username),
            reply_markup=main_menu_keyboard(),
        )
```

В `text_code_handler` строки 83-87:
```python
    user = await link_user_by_code(code, telegram_id)
    if user:
        await update.message.reply_text(
            f"Привязано! Добро пожаловать, {user.full_name or user.username}!",
            reply_markup=main_menu_keyboard(),
        )
```
Заменить на:
```python
    user = await link_user_by_code(code, telegram_id)
    if user:
        await update.message.reply_text(
            WELCOME_AFTER_LINK.format(name=user.full_name or user.username),
            reply_markup=main_menu_keyboard(),
        )
```

- [ ] **Step 5: Запустить тест — должен пройти**

```bash
POSTGRES_HOST=localhost pytest tests/test_bot_start.py::test_welcome_text_contains_menu_hints -v
```
Ожидается: PASS.

- [ ] **Step 6: Запустить все тесты bot — убедиться что link-тесты не сломались**

```bash
POSTGRES_HOST=localhost pytest tests/test_bot_start.py -v
```
Ожидается: 4 passed (3 старых + 1 новый).

- [ ] **Step 7: Commit**

```bash
git add bot/handlers/start.py tests/test_bot_start.py
git commit -m "feat(bot): show menu hints after successful Telegram link"
```

---

## Task 5: Admin view `generate_telegram_code`

**Files:**
- Create: `accounts/admin_views.py`
- Create: `tests/test_admin_invite.py`

**Why:** Это новый POST-эндпоинт, доступный staff-пользователям. TDD-набор покрывает: auth, успех, коллизия retry, 405 на GET.

- [ ] **Step 1: Создать `tests/test_admin_invite.py` с failing-тестами**

```python
from unittest.mock import patch
import pytest
from django.urls import reverse
from django.utils import timezone
from tests.factories import UserFactory, AdminFactory


def _url(user_id):
    return f"/admin/accounts/user/{user_id}/gen-tg-code/"


@pytest.mark.django_db
def test_generate_code_requires_staff(client):
    u = UserFactory()
    resp = client.post(_url(u.id))
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_generate_code_success(client, settings):
    settings.TELEGRAM_BOT_USERNAME = "TestBot"
    admin = AdminFactory()
    u = UserFactory()
    client.force_login(admin)

    resp = client.post(_url(u.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"].isdigit() and len(data["code"]) == 6
    assert "TestBot" in data["copy_text"]
    assert data["code"] in data["copy_text"]

    u.refresh_from_db()
    assert u.telegram_link_code == data["code"]
    assert u.telegram_link_code_expires_at > timezone.now()


@pytest.mark.django_db
def test_generate_code_collision_retry(client):
    admin = AdminFactory()
    existing = UserFactory(telegram_link_code="111111")
    target = UserFactory()
    client.force_login(admin)

    with patch("accounts.admin_views.secrets.randbelow", side_effect=[111111, 222222]):
        resp = client.post(_url(target.id))

    assert resp.status_code == 200
    assert resp.json()["code"] == "222222"
    target.refresh_from_db()
    assert target.telegram_link_code == "222222"


@pytest.mark.django_db
def test_generate_code_get_not_allowed(client):
    admin = AdminFactory()
    u = UserFactory()
    client.force_login(admin)
    resp = client.get(_url(u.id))
    assert resp.status_code == 405
```

- [ ] **Step 2: Запустить тесты — должны упасть (404 на отсутствующий URL)**

```bash
POSTGRES_HOST=localhost pytest tests/test_admin_invite.py -v
```
Ожидается: все 4 FAIL.

- [ ] **Step 3: Создать `accounts/admin_views.py`**

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

- [ ] **Step 4: Запустить тесты — ещё упадут (URL не зарегистрирован)**

```bash
POSTGRES_HOST=localhost pytest tests/test_admin_invite.py -v
```
Ожидается: все 4 FAIL (404). View есть, но не подключена в URLconf. Это сделаем в Task 6.

**НЕ КОММИТИМ** пока URL не подключён — тесты должны проходить перед коммитом.

---

## Task 6: Wire admin UI (UserAdmin: list columns + URL + Media)

**Files:**
- Modify: `accounts/admin.py`
- Modify: `tests/test_admin_invite.py` (добавить UI-тест)

- [ ] **Step 1: Добавить failing UI-тест в `tests/test_admin_invite.py`**

В конец файла:
```python
@pytest.mark.django_db
def test_user_changelist_shows_generate_button(client):
    admin = AdminFactory()
    u = UserFactory(username="bob")
    client.force_login(admin)
    resp = client.get("/admin/accounts/user/")
    assert resp.status_code == 200
    assert b"btn-gen-tg-code" in resp.content
    assert str(u.id).encode() in resp.content
```

- [ ] **Step 2: Запустить — должен упасть (нет кнопки в HTML)**

```bash
POSTGRES_HOST=localhost pytest tests/test_admin_invite.py::test_user_changelist_shows_generate_button -v
```
Ожидается: FAIL (`btn-gen-tg-code` not in content).

- [ ] **Step 3: Обновить `accounts/admin.py`**

Полный файл:
```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import path
from django.utils.html import format_html

from expenses.services.balance import get_balance
from .admin_views import generate_telegram_code
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username", "full_name", "is_admin", "is_active",
        "balance_display", "telegram_status", "telegram_action",
    )
    list_filter = ("is_admin", "is_active")
    search_fields = ("username", "full_name")
    ordering = ("username",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Профиль", {"fields": ("full_name",)}),
        ("Права", {"fields": ("is_active", "is_admin", "is_staff", "is_superuser")}),
        ("Telegram", {"fields": ("telegram_id", "telegram_link_code")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "full_name", "password1", "password2")}),
    )

    class Media:
        js = ("admin/js/telegram_code.js",)

    def balance_display(self, obj):
        return f"{get_balance(obj)} ₸"
    balance_display.short_description = "Баланс"

    def telegram_status(self, obj):
        if obj.telegram_id:
            return format_html('<span style="color:green">привязан</span>')
        return "—"
    telegram_status.short_description = "TG"

    def telegram_action(self, obj):
        if obj.telegram_id:
            return "—"
        return format_html(
            '<button type="button" class="btn-gen-tg-code" data-user-id="{}">Сген. код</button>',
            obj.id,
        )
    telegram_action.short_description = "TG-код"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:user_id>/gen-tg-code/",
                self.admin_site.admin_view(generate_telegram_code),
                name="accounts_user_gen_tg_code",
            ),
        ]
        return custom + urls
```

- [ ] **Step 4: Запустить все Task 5+6 тесты — должны пройти**

```bash
POSTGRES_HOST=localhost pytest tests/test_admin_invite.py -v
```
Ожидается: 5 passed.

- [ ] **Step 5: Запустить полный набор тестов на проверку регрессии**

```bash
POSTGRES_HOST=localhost pytest -v
```
Ожидается: все passed.

- [ ] **Step 6: Commit**

```bash
git add accounts/admin_views.py accounts/admin.py tests/test_admin_invite.py
git commit -m "feat(admin): one-click Telegram invite code generation in user list"
```

---

## Task 7: JS clipboard handler

**Files:**
- Create: `static/admin/js/telegram_code.js`

**Why no automated test:** проект не имеет JS-тест-фреймворка. Smoke через ручной браузер.

- [ ] **Step 1: Создать `static/admin/js/telegram_code.js`**

```javascript
(function () {
  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : null;
  }

  function showToast(text) {
    let toast = document.getElementById("tg-code-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "tg-code-toast";
      toast.style.cssText =
        "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);" +
        "background:#222;color:#fff;padding:12px 20px;border-radius:6px;" +
        "font-size:14px;z-index:9999;box-shadow:0 2px 12px rgba(0,0,0,.3);";
      document.body.appendChild(toast);
    }
    toast.textContent = text;
    toast.style.display = "block";
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { toast.style.display = "none"; }, 4000);
  }

  document.addEventListener("click", async function (e) {
    const btn = e.target.closest(".btn-gen-tg-code");
    if (!btn) return;
    e.preventDefault();

    const userId = btn.dataset.userId;
    const url = `/admin/accounts/user/${userId}/gen-tg-code/`;
    const csrf = getCookie("csrftoken");

    btn.disabled = true;
    btn.textContent = "...";

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const data = await resp.json();
      await navigator.clipboard.writeText(data.copy_text);
      btn.textContent = "✓ " + data.code;
      showToast("Скопировано: код " + data.code + " (действует 10 мин)");
    } catch (err) {
      btn.textContent = "Сген. код";
      btn.disabled = false;
      alert("Ошибка: " + err.message);
    }
  });
})();
```

- [ ] **Step 2: Manual smoke test**

В отдельном терминале:
```bash
cd /Users/adletkartov/projects/manytracker
POSTGRES_HOST=localhost python manage.py collectstatic --noinput
POSTGRES_HOST=localhost python manage.py runserver
```

В браузере:
1. Зайти на `/admin/` под superuser.
2. Перейти `/admin/accounts/user/`.
3. Создать тест-сотрудника (без TG).
4. В колонке «TG-код» нажать «Сген. код».
5. Ожидается: кнопка показывает «✓ <код>», внизу появляется toast.
6. Открыть TextEdit / любой блокнот → Cmd+V → должен вставиться полный текст инструкции с ссылкой `https://t.me/<bot>?start=<код>`.

Если `navigator.clipboard.writeText` не работает в Safari → попробовать Chrome. Clipboard API требует HTTPS либо localhost.

- [ ] **Step 3: Commit**

```bash
git add static/admin/js/telegram_code.js
git commit -m "feat(admin): clipboard-copy JS for Telegram invite codes"
```

---

## Task 8: Manual e2e + Railway deployment

**Files:**
- (документация в этом плане; код уже задеплоен предыдущими тасками)

- [ ] **Step 1: Локальный полный smoke-test**

Запустить весь стек:
```bash
cd /Users/adletkartov/projects/manytracker
docker compose up -d postgres
POSTGRES_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost python manage.py collectstatic --noinput

# Терминал 1
POSTGRES_HOST=localhost TELEGRAM_BOT_USERNAME=<dev_bot_username> \
  python manage.py runserver

# Терминал 2
POSTGRES_HOST=localhost TELEGRAM_BOT_TOKEN=<dev_token> \
  python manage.py run_bot
```

Проверки:
1. В админке создать тест-сотрудника, сгенерить код, скопировать (см. Task 7 Step 2).
2. С другого Telegram-аккаунта перейти по ссылке `https://t.me/<bot>?start=<код>`.
3. Бот отвечает приветствием с памяткой («Балaнс/Расход/Приход/История»).
4. Нажать «Баланс» → ответ «Ваш баланс: 0 ₸».
5. Нажать «Расход» → должны прийти inline-кнопки с категориями. Если категорий нет — кнопка «Другое». **Если не пришёл ответ — проверь логи бота: теперь там должен быть traceback.**
6. Выбрать категорию (или «Другое» + ввести имя) → сумма → /skip → /skip → подтвердить → ✓.
7. «Приход» → сумма → коммент → подтвердить → ✓.
8. «История» → видны обе операции.

- [ ] **Step 2: Открыть Railway dashboard, проверить состав сервисов**

Зайти https://railway.app/ → проект manytracker. Скриншот в текстовом виде описать админу: какие сервисы есть (web, postgres, и есть ли bot).

- [ ] **Step 3: Создать сервис `bot` на Railway**

В проекте Railway:
1. **+ New** → **GitHub Repo** → выбрать `Adletman/manytracker` → ветка `phase-1-mvp`.
2. Settings → **Service Name**: `bot`.
3. Settings → **Start Command**: `python manage.py run_bot`.
4. Variables → скопировать **все** переменные из существующего web-сервиса (DATABASE_URL, TELEGRAM_BOT_TOKEN, DJANGO_SECRET_KEY, и т.д.).
5. Добавить новую переменную **`TELEGRAM_BOT_USERNAME`** (значение — username бота без `@`, например `WedrinkExpenseBot`).
6. На web-сервисе тоже добавить `TELEGRAM_BOT_USERNAME`.
7. **Deploy**.

- [ ] **Step 4: Проверить логи bot-сервиса на Railway**

В Railway → bot service → Logs. Ожидается: `Bot starting...` без traceback.

- [ ] **Step 5: Production e2e smoke**

Через прод-домен:
1. `/admin/` → сгенерить код для реального сотрудника (или тестового).
2. Скопированный текст вставить в чат сотруднику.
3. Сотрудник кликает по ссылке → бот привязывает → видит памятку.
4. Проверить кнопки «Расход» и «Приход» — должны работать.

- [ ] **Step 6: Push ветки**

```bash
git push origin phase-1-mvp
```

**ВАЖНО:** убедиться что юзер действительно хочет пушить в `phase-1-mvp`, а не открывать PR. Спросить перед `git push`.

---

## Self-Review Notes

**Спек-покрытие:**
- ✅ Fix-1 (Procfile + Railway worker) — Task 1 + Task 8
- ✅ Fix-2 (кнопка Расход / error handler) — Task 2
- ✅ Feature (admin invite codes) — Tasks 3-7
- ✅ Welcome memo от бота — Task 4
- ✅ JS clipboard — Task 7
- ✅ Тесты — встроены в каждую кодовую задачу

**Type consistency:** view называется `generate_telegram_code` во всех местах (Task 5 декларация, Task 6 import, Task 5 тесты — URL `/gen-tg-code/`). URL `name="accounts_user_gen_tg_code"` используется только в admin.py — допустимо. CSS-класс `btn-gen-tg-code` единый в Task 6 (template render) и Task 7 (JS selector).

**Placeholders:** нет TODO/TBD; код в каждом шаге полный.
