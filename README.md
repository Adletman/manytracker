# ManyTracker

Система учёта расходов сотрудников. Phase 1: web + Django admin. Phase 2 добавит Telegram-бот.

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

# 4. Миграции + суперпользователь
POSTGRES_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost python manage.py createsuperuser

# 5. Тесты
POSTGRES_HOST=localhost pytest -v

# 6. Запуск
POSTGRES_HOST=localhost python manage.py runserver
```

- Кабинет сотрудника: http://localhost:8000/cabinet/
- Админка: http://localhost:8000/admin/

## Docker (полный стек)

```bash
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## Тесты

```bash
POSTGRES_HOST=localhost pytest -v
```
