# ManyTracker

Система учёта расходов сотрудников для сети Wedrink. Веб-кабинет + Django admin + Telegram-бот.

## Функционал

- **Сотрудник:** баланс, расход/приход, история, файлы-подтверждения, Telegram-бот
- **Админ:** управление пользователями, категориями, пополнениями; таблица всех расходов с Excel-экспортом; dashboard; audit log

## Локальная разработка

```bash
# 1. Python venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Запустить Postgres
docker compose up -d postgres

# 3. Настроить .env
cp .env.example .env
# Отредактировать .env — установить TELEGRAM_BOT_TOKEN

# 4. Миграции + суперпользователь
POSTGRES_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost python manage.py createsuperuser

# 5. Тесты
POSTGRES_HOST=localhost pytest -v

# 6. Запуск веб
POSTGRES_HOST=localhost python manage.py runserver

# 7. Запуск бота (в отдельном терминале)
POSTGRES_HOST=localhost python manage.py run_bot
```

- Кабинет сотрудника: http://localhost:8000/cabinet/
- Админка: http://localhost:8000/admin/
- Dashboard: http://localhost:8000/admin/dashboard/

## Production deploy

```bash
# 1. Клонировать на сервер
git clone <repo-url> /app/manytracker
cd /app/manytracker

# 2. Настроить .env
cp .env.example .env
# Установить:
# - DJANGO_SECRET_KEY (длинная случайная строка)
# - DJANGO_DEBUG=False
# - DJANGO_ALLOWED_HOSTS=yourdomain.com
# - POSTGRES_PASSWORD (надёжный пароль)
# - TELEGRAM_BOT_TOKEN

# 3. Запустить
docker compose up -d --build

# 4. Создать суперпользователя
docker compose exec web python manage.py createsuperuser

# 5. Проверить
curl http://localhost/admin/
```

### HTTPS (Let's Encrypt)

На сервере установите certbot и получите сертификат:

```bash
apt install certbot
certbot certonly --standalone -d yourdomain.com
```

Затем обновите `nginx/nginx.conf` для SSL.

### Бэкапы

```bash
# Ручной бэкап
./scripts/backup.sh

# Автоматический — добавить в crontab:
0 3 * * * cd /app/manytracker && ./scripts/backup.sh >> /var/log/manytracker-backup.log 2>&1
```

## Тесты

```bash
POSTGRES_HOST=localhost pytest -v
```

## Стек

Python 3.12, Django 5.0, PostgreSQL 16, python-telegram-bot 21.5, Docker Compose, nginx, gunicorn
