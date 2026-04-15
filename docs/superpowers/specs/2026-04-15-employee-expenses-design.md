# Система учёта расходов сотрудников — Design Spec

**Дата:** 2026-04-15
**Статус:** Draft → на ревью пользователя

## 1. Цель и контекст

Руководитель выдаёт сотрудникам деньги на рабочие расходы (такси, обеды и т.п.). Нужна система, где:

- Руководитель (админ) пополняет балансы сотрудников и видит все траты.
- Сотрудник через веб-кабинет или Telegram-бот видит свой баланс, заносит траты с категорией, суммой, комментарием и файлом-подтверждением (чек), просматривает свою историю.
- Если сотрудник потратил больше, чем было на балансе — баланс уходит в минус, это означает "руководитель должен сотруднику".
- Админ видит всю активность в одной таблице с фильтрами и экспортом.

**Масштаб:** 30–100 сотрудников. **Валюта:** KZT с копейками. **Хостинг:** собственный VPS с доменом.

## 2. Стек

- **Backend / Admin:** Django (актуальная LTS) + Django admin
- **Telegram-бот:** python-telegram-bot (long polling)
- **БД:** PostgreSQL
- **Файлы:** локальное хранилище `MEDIA_ROOT`, отдача через защищённый Django view
- **Фронт:** Django templates (Jinja2-совместимые или стандартные DTL) + минимальный JS
- **Деплой:** Docker Compose (web, bot, postgres, nginx) + Let's Encrypt
- **Тесты:** pytest + pytest-django

Обоснование Django: админская таблица со всей активностью, фильтрами, поиском и экспортом в CSV — ровно то, что Django admin даёт "из коробки", экономит существенный объём работы.

## 3. Архитектура

Один репозиторий, два процесса в Docker Compose:

1. **web** (gunicorn) — Django: кабинет сотрудника (`/cabinet/`), Django admin (`/admin/`), защищённая отдача файлов.
2. **bot** — Django management command `run_bot`, использует ту же БД через ORM и общие сервисы.

Общая бизнес-логика вынесена в `expenses/services/` и переиспользуется веб-view'ами и bot-handlers. Это даёт единое поведение на обоих каналах и упрощает тестирование.

## 4. Модель данных

### User (кастомная модель, расширяет `AbstractUser`)
- `username`, `password` (argon2)
- `full_name`
- `is_admin: bool`
- `telegram_id: bigint | null` (уникальный)
- `telegram_link_code: str | null` (6 цифр, TTL 10 минут, одноразовый)
- `telegram_link_code_expires_at: datetime | null`
- `created_at`

### ExpenseCategory
- `name` (unique)
- `is_active: bool`
- `sort_order: int`

Управляется админом через Django admin.

### Topup (пополнение баланса админом)
- `user` (FK → User)
- `amount` (DECIMAL(12,2), > 0)
- `date` (date, может быть задним числом)
- `comment` (text, nullable)
- `created_by` (FK → User, админ)
- `created_at` (datetime)

### Expense (трата сотрудника)
- `user` (FK → User)
- `category` (FK → ExpenseCategory, nullable — если "Другое")
- `custom_category_name` (str, nullable — если `category` null)
- `amount` (DECIMAL(12,2), > 0)
- `date` (date, может быть задним числом через веб; в боте — только сегодня)
- `comment` (text, nullable)
- `created_via` (enum: `web` | `telegram`)
- `created_at`, `updated_at`
- `is_deleted: bool` (soft delete)

**Инвариант:** либо `category` задана, либо `custom_category_name` задан — валидация на уровне модели.

### ExpenseAttachment
- `expense` (FK → Expense, cascade)
- `file` (FileField, хранится под UUID-именем)
- `original_name` (str)
- `mime_type` (str)
- `size: int` (bytes)
- `uploaded_at`

До 5 файлов на трату, до 10 МБ каждый, whitelist MIME: `image/jpeg`, `image/png`, `application/pdf`, `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.

### AuditLog
- `user` (FK → User, кто совершил действие)
- `action` (enum: `create` | `update` | `delete`)
- `entity` (enum: `expense` | `topup`)
- `entity_id: int`
- `diff` (JSON — что поменялось)
- `created_at`

Пишется во все операции create/update/delete над `Expense` и `Topup`. Read-only в админке.

### Расчёт баланса
Вычисляется на лету:

```
balance(user) = SUM(Topup.amount WHERE user=user)
              - SUM(Expense.amount WHERE user=user AND is_deleted=false)
```

При 30–100 сотрудниках денормализация не нужна. Если через годы данные станут большими, добавим кеширование/материализованное представление — не сейчас.

## 5. Потоки

### 5.1 Сотрудник — веб-кабинет
1. Логин (username + пароль, выдан админом).
2. Главная: текущий баланс (крупно), кнопка **Добавить трату**, история (пополнения + траты, фильтр по диапазону дат).
3. **Добавить трату** — форма:
   - Категория (select активных `ExpenseCategory` + опция "Другое")
   - Если "Другое" — поле для своего названия
   - Сумма (> 0)
   - Дата (по умолчанию сегодня, допустимый диапазон: [сегодня − 2 года, сегодня])
   - Комментарий (опционально)
   - Файлы (multi-upload, до 5, до 10 МБ каждый, whitelist типов)
4. При сабмите, если баланс после траты становится < 0, форма возвращается с предупреждением: "Баланс станет −X ₸. Продолжить?" и скрытым флагом `confirm_negative=true`. Второй сабмит сохраняет запись.
5. История: свои траты и пополнения, по убыванию даты. Для своих трат, у которых `created_at` < 24 часов назад, показываются кнопки **Редактировать** и **Удалить**. Иначе — read-only.
6. Профиль: **Привязать Telegram** → сгенерировать 6-значный код (TTL 10 минут), показать инструкцию "Отправьте боту `/start <код>`". Если уже привязан — показать "Привязано к Telegram ID X" и кнопку "Отвязать".

### 5.2 Сотрудник — Telegram-бот
1. `/start` без аргумента → "Введите код привязки из веб-кабинета".
2. `/start <код>` или отправка кода текстом → если код валиден и не истёк → привязка, приветствие с главным меню.
3. Главное меню (reply-keyboard или inline): **Баланс**, **Добавить трату**, **История**.
4. **Добавить трату** — FSM:
   - Выбор категории (inline-keyboard из активных + "Другое")
   - Если "Другое" — попросить ввести название текстом
   - Сумма (текстом, валидация)
   - Комментарий (или "Пропустить")
   - Файл (или "Пропустить"). Только один файл через бота на первой итерации. `date` = сегодня.
   - Подтверждение → сохранение → "Готово. Баланс: X ₸"
   - Если баланс после траты < 0 — кнопки "Подтвердить (в минус)" / "Отменить".
5. **Баланс** — текущая сумма.
6. **История** — последние 10 операций (пополнения + траты).

### 5.3 Админ — Django admin
1. Логин на `/admin/`.
2. **Users:** список с колонкой "Баланс", поиск по имени/username, создание (username + временный пароль), сброс пароля, блокировка (`is_active=False`).
3. **Topups:** таблица всех пополнений; создание (user, amount, date, comment).
4. **Expenses:** таблица всех трат. Колонки: `date`, `user`, `category` (или `custom_category_name`), `amount`, `comment` (обрезанный), `attachments_count`, `created_via`, `created_at`. Фильтры: `user`, `category`, `created_via`, диапазон `date`. Поиск по `comment`. Action: export в CSV.
5. **ExpenseCategories:** CRUD.
6. **AuditLog:** read-only, фильтрация по пользователю/сущности/дате.
7. **Dashboard** (кастомная страница `/admin/dashboard/`): таблица всех сотрудников с их текущими балансами; общая сумма трат за выбранный период; топ-5 категорий.

## 6. Структура кода

```
myproject/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── manage.py
├── config/                   # Django project
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                 # User + login + Telegram linking
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── admin.py
│   └── urls.py
├── expenses/
│   ├── models.py             # ExpenseCategory, Topup, Expense, ExpenseAttachment, AuditLog
│   ├── services/
│   │   ├── balance.py        # get_balance(user)
│   │   ├── expenses.py       # create/update/delete_expense (+ audit, + 24h rule)
│   │   └── topups.py
│   ├── views.py              # cabinet, history, expense_form, file_download
│   ├── forms.py
│   ├── admin.py              # Django admin + dashboard
│   └── urls.py
├── bot/
│   ├── management/commands/run_bot.py
│   ├── handlers/
│   │   ├── start.py
│   │   ├── menu.py
│   │   ├── balance.py
│   │   ├── add_expense.py    # FSM
│   │   └── history.py
│   └── keyboards.py
├── templates/
│   ├── base.html
│   ├── accounts/{login,profile}.html
│   └── expenses/{cabinet,history,expense_form}.html
├── static/
├── media/                    # MEDIA_ROOT
└── tests/
```

**Принцип:** бизнес-логика — только в `expenses/services/`. Views и handlers — тонкие обёртки. Одинаковое поведение в веб и боте, простое тестирование.

## 7. Валидация и ошибки

- **Сумма:** `DECIMAL(12,2)`, > 0, ≤ 999 999 999.99 ₸
- **Дата:** в диапазоне [сегодня − 2 года, сегодня]
- **Файлы:** whitelist MIME, ≤ 10 МБ, ≤ 5 на трату; оригинальное имя сохраняется, на диске — UUID
- **Отрицательный баланс:** разрешён, но требует явного подтверждения (`confirm_negative` в веб, кнопка в боте)
- **Категория/другое:** ровно одно из двух полей должно быть заполнено
- Все сообщения — на русском, человеческим языком

## 8. Безопасность

- Пароли — argon2, минимум 8 символов
- CSRF на всех POST-формах (встроено в Django)
- Отдача файлов: view проверяет, что `request.user` — владелец траты или админ. Nginx не раздаёт `/media/` напрямую.
- Rate limit на логин: 5 попыток / 15 минут (django-axes)
- HTTPS обязателен (nginx + Let's Encrypt)
- `DEBUG=False` в production; `SECRET_KEY`, `DATABASE_URL`, `TELEGRAM_BOT_TOKEN` — из env
- Telegram-код привязки: 6 цифр, TTL 10 минут, одноразовый, хранится в User
- Бэкапы: ежедневный `pg_dump` в Docker cron, хранение 14 дней; бэкап `media/` — tar.gz

## 9. Тесты (pytest + pytest-django)

- **services:** `balance.get_balance`, `expenses.create/update/delete`, правило 24 ч, `topups.create` — unit
- **permissions:** сотрудник видит только свои траты; не-админ не может в `/admin/`; файл доступен только владельцу и админу
- **forms:** валидация суммы, даты, файлов, правила "category xor custom_category_name"
- **views integration:** логин, создание траты (обычный случай и минус), загрузка файла, история, фильтры
- **bot handlers:** привязка кода, FSM-диалог добавления траты (мокаем telegram API)
- **audit log:** каждая операция на Expense/Topup пишет запись

Цель покрытия: ≥ 80% на `expenses/services/`.

## 10. Деплой

- `docker-compose.yml`: сервисы `web`, `bot`, `postgres`, `nginx`
- `.env`: `SECRET_KEY`, `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `ALLOWED_HOSTS`, `MEDIA_ROOT`
- `nginx` терминирует TLS (Let's Encrypt через certbot в отдельном контейнере или на хосте), проксирует на gunicorn, статика из volume
- Первый запуск: `python manage.py migrate && createsuperuser`
- Мониторинг (первая итерация): логи в stdout, `docker compose logs`

## 11. Что НЕ входит в эту итерацию (YAGNI)

- Мультивалютность
- Уведомления (email, push, Telegram) о низком балансе или о пополнении
- Отчёты/графики за кастомные периоды (помимо базового dashboard)
- Интеграция с бухгалтерией, OCR чеков
- Мобильные нативные приложения
- Роли кроме `employee` / `admin` (без менеджеров среднего уровня)
- Multi-file загрузка через Telegram-бота
- Редактирование трат через бота (только через веб)
