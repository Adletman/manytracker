# Phase 1: Foundation + MVP Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Working web-based expense tracking system — employees log in, see their KZT balance, submit expenses with category/amount/date/comment/attachments, view their history, and edit/delete within 24 h. Admin manages users, categories, top-ups, and views all activity through Django admin with filters and CSV export. No Telegram bot in this phase.

**Architecture:** Django 5.x monolith with custom User model. Business logic isolated in `expenses/services/` so Phase 2 (Telegram bot) can reuse it. Django admin provides the entire admin UI. Postgres for data, local filesystem for uploaded files. Runs in Docker Compose for dev.

**Tech Stack:** Python 3.12, Django 5.0 LTS, PostgreSQL 16, psycopg[binary], pytest + pytest-django + factory-boy, Docker Compose, gunicorn, argon2-cffi.

**Spec:** `docs/superpowers/specs/2026-04-15-employee-expenses-design.md`

---

## File Structure

```
my-project/
├── docker-compose.yml            # Task 2
├── Dockerfile                    # Task 2
├── requirements.txt              # Task 1
├── .env.example                  # Task 2
├── pytest.ini                    # Task 1
├── manage.py                     # Task 1 (django-admin startproject)
├── config/                       # Django project
│   ├── __init__.py
│   ├── settings.py               # Task 3
│   ├── urls.py                   # Tasks 6, 18-22
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                     # Custom User, login
│   ├── apps.py
│   ├── models.py                 # Task 4 — User
│   ├── managers.py               # Task 4 — UserManager
│   ├── admin.py                  # Task 23
│   ├── forms.py                  # Task 6 — LoginForm
│   ├── views.py                  # Task 6 — login/logout
│   ├── urls.py                   # Task 6
│   └── migrations/
├── expenses/                     # Core domain
│   ├── apps.py
│   ├── models.py                 # Tasks 7-11
│   ├── validators.py             # Task 10 — file validator
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audit.py              # Task 11 — write_audit helper
│   │   ├── balance.py            # Task 12 — get_balance
│   │   ├── topups.py             # Task 13 — create_topup
│   │   └── expenses.py           # Tasks 14-16 — CRUD + 24h rule
│   ├── forms.py                  # Task 17 — ExpenseForm
│   ├── views.py                  # Tasks 18-22
│   ├── admin.py                  # Tasks 24-27
│   ├── urls.py                   # Task 18
│   └── migrations/
├── templates/
│   ├── base.html                 # Task 6
│   ├── accounts/login.html       # Task 6
│   └── expenses/
│       ├── cabinet.html          # Task 18
│       ├── expense_form.html     # Task 19
│       ├── history.html          # Task 21
│       └── confirm_delete.html   # Task 20
├── static/
├── media/                        # gitignored
└── tests/
    ├── __init__.py
    ├── conftest.py               # Task 1 — fixtures
    ├── factories.py              # Task 11 — factory-boy
    ├── test_models.py            # Tasks 7-11
    ├── test_balance.py           # Task 12
    ├── test_topup_service.py     # Task 13
    ├── test_expense_service.py   # Tasks 14-16
    ├── test_forms.py             # Task 17
    ├── test_views_cabinet.py     # Task 18
    ├── test_views_expense.py     # Tasks 19-20
    ├── test_views_history.py     # Task 21
    ├── test_file_download.py     # Task 22
    ├── test_permissions.py       # Task 28
    └── test_admin.py             # Tasks 24-27
```

---

## Task 1: Project scaffolding (requirements, Django project, pytest)

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `manage.py`, `config/__init__.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`, `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Write `requirements.txt`**

```
Django==5.0.8
psycopg[binary]==3.2.1
argon2-cffi==23.1.0
gunicorn==23.0.0
python-dotenv==1.0.1
Pillow==10.4.0
pytest==8.3.2
pytest-django==4.9.0
factory-boy==3.3.1
```

- [ ] **Step 2: Create venv and install**

```bash
cd ~/Documents/my-project
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 3: Bootstrap Django project**

```bash
django-admin startproject config .
```

This creates `manage.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`.

- [ ] **Step 4: Write `pytest.ini`**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
addopts = -v --tb=short
```

- [ ] **Step 5: Write `tests/__init__.py`**

Empty file:

```bash
touch tests/__init__.py
```

- [ ] **Step 6: Write `tests/conftest.py`**

```python
import pytest


@pytest.fixture
def user_data():
    return {
        "username": "alice",
        "password": "secretpass123",
        "full_name": "Alice Worker",
    }
```

- [ ] **Step 7: Verify Django imports**

```bash
python -c "import django; print(django.get_version())"
```

Expected: `5.0.8`

- [ ] **Step 8: Commit**

```bash
git add requirements.txt pytest.ini manage.py config/ tests/
git commit -m "chore: bootstrap Django 5 project with pytest"
```

---

## Task 2: Docker Compose + Dockerfile + .env.example

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.env.example`

- [ ] **Step 1: Write `Dockerfile`**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/media /app/staticfiles

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

- [ ] **Step 2: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./media:/app/media
      - ./staticfiles:/app/staticfiles
    ports:
      - "8000:8000"
    depends_on:
      - postgres

volumes:
  pg_data:
```

- [ ] **Step 3: Write `.env.example`**

```
DJANGO_SECRET_KEY=change-me-to-a-long-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=manytracker
POSTGRES_USER=manytracker
POSTGRES_PASSWORD=devpassword
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

- [ ] **Step 4: Copy to `.env` locally**

```bash
cp .env.example .env
```

(`.env` is already gitignored.)

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .env.example
git commit -m "chore: add Docker Compose with postgres and web services"
```

---

## Task 3: Configure Django settings from env

**Files:**
- Modify: `config/settings.py`

- [ ] **Step 1: Rewrite `config/settings.py`**

```python
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "expenses",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "manytracker"),
        "USER": os.environ.get("POSTGRES_USER", "manytracker"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Almaty"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/cabinet/"
LOGOUT_REDIRECT_URL = "/login/"

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
```

- [ ] **Step 2: Create `static/` placeholder**

```bash
mkdir -p static media
touch static/.keep
```

- [ ] **Step 3: Verify config loads**

```bash
python manage.py check
```

Expected: `System check identified no issues`. If it complains about missing `accounts`/`expenses` apps, that's fine — we'll create them in next tasks. If so, temporarily comment them out in `INSTALLED_APPS`, run check, uncomment.

- [ ] **Step 4: Commit**

```bash
git add config/settings.py static/.keep
git commit -m "feat(config): wire Django settings to env vars and postgres"
```

---

## Task 4: Custom User model

**Files:**
- Create: `accounts/__init__.py`, `accounts/apps.py`, `accounts/models.py`, `accounts/managers.py`, `accounts/migrations/__init__.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Create `accounts` app structure**

```bash
python manage.py startapp accounts
```

- [ ] **Step 2: Write `accounts/managers.py`**

```python
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, password, **extra):
        if not username:
            raise ValueError("Username is required")
        user = self.model(username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra):
        extra.setdefault("is_admin", False)
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra)

    def create_superuser(self, username, password=None, **extra):
        extra.setdefault("is_admin", True)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(username, password, **extra)
```

- [ ] **Step 3: Write `accounts/models.py`**

```python
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=64, unique=True)
    full_name = models.CharField(max_length=128, blank=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_link_code = models.CharField(max_length=6, null=True, blank=True)
    telegram_link_code_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.full_name or self.username
```

- [ ] **Step 4: Write `accounts/apps.py`**

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
```

- [ ] **Step 5: Write failing test `tests/test_models.py`**

```python
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_create_user_hashes_password():
    user = User.objects.create_user(username="alice", password="secretpass123", full_name="Alice")
    assert user.username == "alice"
    assert user.check_password("secretpass123")
    assert not user.is_admin
    assert user.is_active


@pytest.mark.django_db
def test_create_superuser_flags():
    admin = User.objects.create_superuser(username="boss", password="adminpass123")
    assert admin.is_admin
    assert admin.is_staff
    assert admin.is_superuser
```

- [ ] **Step 6: Make migrations**

```bash
python manage.py makemigrations accounts
```

Expected: `Migrations for 'accounts': 0001_initial.py`

- [ ] **Step 7: Bring up postgres and run migrations**

```bash
docker compose up -d postgres
# wait ~3s for postgres to be ready
POSTGRES_HOST=localhost python manage.py migrate
```

- [ ] **Step 8: Run tests**

```bash
POSTGRES_HOST=localhost pytest tests/test_models.py -v
```

Expected: both tests PASS.

- [ ] **Step 9: Commit**

```bash
git add accounts/ tests/test_models.py
git commit -m "feat(accounts): add custom User model with UserManager"
```

---

## Task 5: Expenses app scaffolding + ExpenseCategory

**Files:**
- Create: `expenses/` app
- Modify: `expenses/models.py`
- Test: `tests/test_models.py` (append)

- [ ] **Step 1: Create app**

```bash
python manage.py startapp expenses
mkdir -p expenses/services
touch expenses/services/__init__.py
```

- [ ] **Step 2: Write `expenses/models.py` — ExpenseCategory first**

```python
from django.db import models


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name
```

- [ ] **Step 3: Append test to `tests/test_models.py`**

```python
from expenses.models import ExpenseCategory


@pytest.mark.django_db
def test_expense_category_ordering():
    c1 = ExpenseCategory.objects.create(name="Обед", sort_order=2)
    c2 = ExpenseCategory.objects.create(name="Такси", sort_order=1)
    names = list(ExpenseCategory.objects.values_list("name", flat=True))
    assert names == ["Такси", "Обед"]
```

- [ ] **Step 4: Migrate + run tests**

```bash
python manage.py makemigrations expenses
POSTGRES_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost pytest tests/test_models.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add expenses/
git commit -m "feat(expenses): add ExpenseCategory model"
```

---

## Task 6: Login page + base template

**Files:**
- Create: `accounts/forms.py`, `accounts/views.py`, `accounts/urls.py`, `templates/base.html`, `templates/accounts/login.html`
- Modify: `config/urls.py`

- [ ] **Step 1: Write `accounts/forms.py`**

```python
from django import forms
from django.contrib.auth import authenticate


class LoginForm(forms.Form):
    username = forms.CharField(label="Логин", max_length=64)
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        user = authenticate(
            username=cleaned.get("username"),
            password=cleaned.get("password"),
        )
        if user is None:
            raise forms.ValidationError("Неверный логин или пароль")
        cleaned["user"] = user
        return cleaned
```

- [ ] **Step 2: Write `accounts/views.py`**

```python
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from .forms import LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("/cabinet/")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.cleaned_data["user"])
        return redirect("/cabinet/")
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("/login/")
```

- [ ] **Step 3: Write `accounts/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]
```

- [ ] **Step 4: Modify `config/urls.py`**

```python
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 5: Write `templates/base.html`**

```html
{% load static %}
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}ManyTracker{% endblock %}</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
  form { display: flex; flex-direction: column; gap: .5rem; }
  label { font-weight: bold; }
  input, select, textarea, button { padding: .5rem; font-size: 1rem; }
  .errors { color: #c00; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: .5rem; border-bottom: 1px solid #eee; }
  .balance { font-size: 2rem; font-weight: bold; }
  .balance.negative { color: #c00; }
</style>
</head>
<body>
{% if user.is_authenticated %}
  <nav>
    <a href="/cabinet/">Кабинет</a> |
    <a href="/history/">История</a> |
    <a href="/logout/">Выйти ({{ user.full_name|default:user.username }})</a>
  </nav>
  <hr>
{% endif %}
{% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 6: Write `templates/accounts/login.html`**

```html
{% extends "base.html" %}
{% block title %}Вход — ManyTracker{% endblock %}
{% block content %}
<h1>Вход</h1>
<form method="post">
  {% csrf_token %}
  {% if form.non_field_errors %}
    <div class="errors">{{ form.non_field_errors }}</div>
  {% endif %}
  {% for field in form %}
    <label>{{ field.label }}</label>
    {{ field }}
  {% endfor %}
  <button type="submit">Войти</button>
</form>
{% endblock %}
```

- [ ] **Step 7: Smoke test**

```bash
POSTGRES_HOST=localhost python manage.py runserver
```

Open `http://localhost:8000/login/` in browser. Form should render. Stop the server with Ctrl+C.

- [ ] **Step 8: Commit**

```bash
git add accounts/forms.py accounts/views.py accounts/urls.py config/urls.py templates/
git commit -m "feat(accounts): add login/logout views and base template"
```

---

## Task 7: Topup model

**Files:**
- Modify: `expenses/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Add `Topup` to `expenses/models.py`**

```python
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal


class Topup(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="topups",
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date = models.DateField()
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_topups",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"+{self.amount} ₸ → {self.user} ({self.date})"
```

Keep `ExpenseCategory` as-is. Add the imports at the top of the file.

- [ ] **Step 2: Append test to `tests/test_models.py`**

```python
from datetime import date
from decimal import Decimal
from expenses.models import Topup


@pytest.mark.django_db
def test_topup_creation():
    user = User.objects.create_user(username="alice", password="x" * 10)
    admin = User.objects.create_superuser(username="boss", password="x" * 10)
    t = Topup.objects.create(
        user=user, amount=Decimal("50000.00"), date=date(2026, 4, 1),
        comment="Аванс", created_by=admin,
    )
    assert t.amount == Decimal("50000.00")
    assert t.user == user
```

- [ ] **Step 3: Migrate + run tests**

```bash
python manage.py makemigrations expenses
POSTGRES_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost pytest tests/test_models.py -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add expenses/models.py expenses/migrations/ tests/test_models.py
git commit -m "feat(expenses): add Topup model"
```

---

## Task 8: Expense model with xor invariant

**Files:**
- Modify: `expenses/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Append `Expense` to `expenses/models.py`**

```python
class Expense(models.Model):
    CREATED_VIA_WEB = "web"
    CREATED_VIA_TELEGRAM = "telegram"
    CREATED_VIA_CHOICES = [
        (CREATED_VIA_WEB, "Веб"),
        (CREATED_VIA_TELEGRAM, "Telegram"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="expenses",
    )
    custom_category_name = models.CharField(max_length=64, blank=True)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date = models.DateField()
    comment = models.TextField(blank=True)
    created_via = models.CharField(
        max_length=16, choices=CREATED_VIA_CHOICES, default=CREATED_VIA_WEB,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(category__isnull=False, custom_category_name="")
                    | models.Q(category__isnull=True) & ~models.Q(custom_category_name="")
                ),
                name="category_xor_custom",
            ),
        ]

    def category_display(self):
        return self.category.name if self.category else self.custom_category_name

    def __str__(self):
        return f"-{self.amount} ₸ {self.category_display()} ({self.user})"
```

- [ ] **Step 2: Append test**

```python
from expenses.models import Expense, ExpenseCategory
from django.db.utils import IntegrityError


@pytest.mark.django_db
def test_expense_requires_category_or_custom():
    user = User.objects.create_user(username="alice", password="x" * 10)
    cat = ExpenseCategory.objects.create(name="Такси")

    # valid: category set
    e1 = Expense.objects.create(
        user=user, category=cat, amount=Decimal("1500"), date=date(2026, 4, 1),
    )
    assert e1.category_display() == "Такси"

    # valid: custom_category_name set
    e2 = Expense.objects.create(
        user=user, custom_category_name="Парковка", amount=Decimal("500"),
        date=date(2026, 4, 1),
    )
    assert e2.category_display() == "Парковка"

    # invalid: neither — DB constraint
    with pytest.raises(IntegrityError):
        Expense.objects.create(user=user, amount=Decimal("100"), date=date(2026, 4, 1))
```

- [ ] **Step 3: Migrate + run**

```bash
python manage.py makemigrations expenses
POSTGRES_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost pytest tests/test_models.py -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add expenses/models.py expenses/migrations/ tests/test_models.py
git commit -m "feat(expenses): add Expense model with category xor constraint"
```

---

## Task 9: ExpenseAttachment model + file validator

**Files:**
- Create: `expenses/validators.py`
- Modify: `expenses/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write `expenses/validators.py`**

```python
from django.core.exceptions import ValidationError

ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_attachment(file):
    if file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(f"Файл больше 10 МБ ({file.size} байт)")
    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_MIME:
        raise ValidationError(f"Недопустимый тип файла: {content_type}")
```

- [ ] **Step 2: Add `ExpenseAttachment` to `expenses/models.py`**

```python
import uuid
from .validators import validate_attachment


def attachment_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"attachments/{uuid.uuid4().hex}.{ext}"


class ExpenseAttachment(models.Model):
    expense = models.ForeignKey(
        Expense, on_delete=models.CASCADE, related_name="attachments",
    )
    file = models.FileField(upload_to=attachment_upload_path, validators=[validate_attachment])
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=128)
    size = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

- [ ] **Step 3: Append test**

```python
from django.core.files.uploadedfile import SimpleUploadedFile
from expenses.validators import validate_attachment, MAX_FILE_SIZE_BYTES
from django.core.exceptions import ValidationError


def test_validate_attachment_size():
    f = SimpleUploadedFile("big.pdf", b"x" * (MAX_FILE_SIZE_BYTES + 1), content_type="application/pdf")
    with pytest.raises(ValidationError):
        validate_attachment(f)


def test_validate_attachment_mime_whitelist():
    f = SimpleUploadedFile("bad.exe", b"x", content_type="application/x-msdownload")
    with pytest.raises(ValidationError):
        validate_attachment(f)


def test_validate_attachment_accepts_pdf():
    f = SimpleUploadedFile("ok.pdf", b"x", content_type="application/pdf")
    validate_attachment(f)  # should not raise
```

- [ ] **Step 4: Migrate + run**

```bash
python manage.py makemigrations expenses
POSTGRES_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost pytest tests/test_models.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add expenses/validators.py expenses/models.py expenses/migrations/ tests/test_models.py
git commit -m "feat(expenses): add ExpenseAttachment with size and MIME validators"
```

---

## Task 10: AuditLog model + write helper

**Files:**
- Modify: `expenses/models.py`
- Create: `expenses/services/audit.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Add `AuditLog` to `expenses/models.py`**

```python
class AuditLog(models.Model):
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_CHOICES = [
        (ACTION_CREATE, "create"),
        (ACTION_UPDATE, "update"),
        (ACTION_DELETE, "delete"),
    ]

    ENTITY_EXPENSE = "expense"
    ENTITY_TOPUP = "topup"
    ENTITY_CHOICES = [
        (ENTITY_EXPENSE, "expense"),
        (ENTITY_TOPUP, "topup"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    entity = models.CharField(max_length=16, choices=ENTITY_CHOICES)
    entity_id = models.BigIntegerField()
    diff = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
```

- [ ] **Step 2: Write `expenses/services/audit.py`**

```python
from expenses.models import AuditLog


def write_audit(*, user, action, entity, entity_id, diff=None):
    return AuditLog.objects.create(
        user=user,
        action=action,
        entity=entity,
        entity_id=entity_id,
        diff=diff or {},
    )
```

- [ ] **Step 3: Append test**

```python
from expenses.services.audit import write_audit
from expenses.models import AuditLog


@pytest.mark.django_db
def test_write_audit_creates_entry():
    user = User.objects.create_user(username="alice", password="x" * 10)
    entry = write_audit(
        user=user, action=AuditLog.ACTION_CREATE,
        entity=AuditLog.ENTITY_EXPENSE, entity_id=1,
        diff={"amount": "1500.00"},
    )
    assert AuditLog.objects.count() == 1
    assert entry.diff["amount"] == "1500.00"
```

- [ ] **Step 4: Migrate + run**

```bash
python manage.py makemigrations expenses
POSTGRES_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost pytest tests/test_models.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add expenses/models.py expenses/services/audit.py expenses/migrations/ tests/test_models.py
git commit -m "feat(expenses): add AuditLog model and write_audit helper"
```

---

## Task 11: factory-boy fixtures

**Files:**
- Create: `tests/factories.py`

- [ ] **Step 1: Write `tests/factories.py`**

```python
from datetime import date
from decimal import Decimal
import factory
from django.contrib.auth import get_user_model
from expenses.models import ExpenseCategory, Expense, Topup

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    full_name = factory.Faker("name")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "testpass1234")
        if create:
            self.save()


class AdminFactory(UserFactory):
    is_admin = True
    is_staff = True
    is_superuser = True


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExpenseCategory

    name = factory.Sequence(lambda n: f"Категория {n}")


class TopupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Topup

    user = factory.SubFactory(UserFactory)
    amount = Decimal("10000.00")
    date = factory.LazyFunction(date.today)
    created_by = factory.SubFactory(AdminFactory)


class ExpenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Expense

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    amount = Decimal("1500.00")
    date = factory.LazyFunction(date.today)
```

- [ ] **Step 2: Smoke test in shell**

```bash
POSTGRES_HOST=localhost python manage.py shell -c "
from tests.factories import UserFactory, ExpenseFactory
from django.db import transaction
with transaction.atomic():
    u = UserFactory.build(); print(u.username)
"
```

Expected: prints a username like `user0`.

- [ ] **Step 3: Commit**

```bash
git add tests/factories.py
git commit -m "test: add factory-boy fixtures"
```

---

## Task 12: balance.get_balance service

**Files:**
- Create: `expenses/services/balance.py`
- Test: `tests/test_balance.py`

- [ ] **Step 1: Write failing test `tests/test_balance.py`**

```python
from decimal import Decimal
from datetime import date
import pytest
from tests.factories import UserFactory, TopupFactory, ExpenseFactory, AdminFactory
from expenses.services.balance import get_balance


@pytest.mark.django_db
def test_balance_zero_for_new_user():
    u = UserFactory()
    assert get_balance(u) == Decimal("0.00")


@pytest.mark.django_db
def test_balance_sums_topups_minus_expenses():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("50000.00"), created_by=admin)
    TopupFactory(user=u, amount=Decimal("20000.00"), created_by=admin)
    ExpenseFactory(user=u, amount=Decimal("15000.00"))
    ExpenseFactory(user=u, amount=Decimal("5000.00"))
    assert get_balance(u) == Decimal("50000.00")


@pytest.mark.django_db
def test_balance_ignores_soft_deleted_expenses():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000.00"), created_by=admin)
    ExpenseFactory(user=u, amount=Decimal("3000.00"), is_deleted=True)
    ExpenseFactory(user=u, amount=Decimal("2000.00"))
    assert get_balance(u) == Decimal("8000.00")


@pytest.mark.django_db
def test_balance_can_be_negative():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("1000.00"), created_by=admin)
    ExpenseFactory(user=u, amount=Decimal("2500.00"))
    assert get_balance(u) == Decimal("-1500.00")
```

- [ ] **Step 2: Run test to see failure**

```bash
POSTGRES_HOST=localhost pytest tests/test_balance.py -v
```

Expected: FAIL (`ModuleNotFoundError: expenses.services.balance`).

- [ ] **Step 3: Implement `expenses/services/balance.py`**

```python
from decimal import Decimal
from django.db.models import Sum
from expenses.models import Topup, Expense


def get_balance(user) -> Decimal:
    topups_sum = Topup.objects.filter(user=user).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
    expenses_sum = (
        Expense.objects.filter(user=user, is_deleted=False)
        .aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
    )
    return topups_sum - expenses_sum
```

- [ ] **Step 4: Run tests**

```bash
POSTGRES_HOST=localhost pytest tests/test_balance.py -v
```

Expected: all 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add expenses/services/balance.py tests/test_balance.py
git commit -m "feat(expenses): add get_balance service"
```

---

## Task 13: topups.create_topup service

**Files:**
- Create: `expenses/services/topups.py`
- Test: `tests/test_topup_service.py`

- [ ] **Step 1: Write failing test `tests/test_topup_service.py`**

```python
from datetime import date
from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory
from expenses.services.topups import create_topup
from expenses.models import Topup, AuditLog


@pytest.mark.django_db
def test_create_topup_writes_record_and_audit():
    u = UserFactory()
    admin = AdminFactory()
    topup = create_topup(
        admin=admin, user=u, amount=Decimal("50000.00"),
        topup_date=date(2026, 4, 1), comment="Аванс",
    )
    assert Topup.objects.count() == 1
    assert topup.amount == Decimal("50000.00")
    assert AuditLog.objects.filter(entity="topup", action="create").count() == 1


@pytest.mark.django_db
def test_create_topup_rejects_non_positive():
    u = UserFactory()
    admin = AdminFactory()
    with pytest.raises(ValueError):
        create_topup(admin=admin, user=u, amount=Decimal("0"), topup_date=date.today())
```

- [ ] **Step 2: Run → FAIL**

```bash
POSTGRES_HOST=localhost pytest tests/test_topup_service.py -v
```

- [ ] **Step 3: Write `expenses/services/topups.py`**

```python
from decimal import Decimal
from django.db import transaction
from expenses.models import Topup, AuditLog
from expenses.services.audit import write_audit


def create_topup(*, admin, user, amount: Decimal, topup_date, comment: str = ""):
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    with transaction.atomic():
        topup = Topup.objects.create(
            user=user, amount=amount, date=topup_date, comment=comment,
            created_by=admin,
        )
        write_audit(
            user=admin, action=AuditLog.ACTION_CREATE,
            entity=AuditLog.ENTITY_TOPUP, entity_id=topup.id,
            diff={"amount": str(amount), "user_id": user.id, "date": topup_date.isoformat()},
        )
    return topup
```

- [ ] **Step 4: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_topup_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add expenses/services/topups.py tests/test_topup_service.py
git commit -m "feat(expenses): add create_topup service with audit logging"
```

---

## Task 14: expenses.create_expense service (with negative confirm)

**Files:**
- Create: `expenses/services/expenses.py`
- Test: `tests/test_expense_service.py`

- [ ] **Step 1: Write failing test `tests/test_expense_service.py`**

```python
from datetime import date
from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory, CategoryFactory, TopupFactory
from expenses.services.expenses import create_expense, NegativeBalanceError
from expenses.models import Expense, AuditLog


@pytest.mark.django_db
def test_create_expense_happy_path():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000.00"), created_by=admin)
    cat = CategoryFactory(name="Такси")
    e = create_expense(
        user=u, category=cat, custom_name="",
        amount=Decimal("1500.00"), expense_date=date(2026, 4, 1),
        comment="", created_via="web",
    )
    assert e.pk is not None
    assert AuditLog.objects.filter(entity="expense", action="create").count() == 1


@pytest.mark.django_db
def test_create_expense_rejects_negative_without_confirm():
    u = UserFactory()
    cat = CategoryFactory()
    with pytest.raises(NegativeBalanceError):
        create_expense(
            user=u, category=cat, custom_name="",
            amount=Decimal("1000.00"), expense_date=date(2026, 4, 1),
            comment="", created_via="web",
        )


@pytest.mark.django_db
def test_create_expense_allows_negative_with_confirm():
    u = UserFactory()
    cat = CategoryFactory()
    e = create_expense(
        user=u, category=cat, custom_name="",
        amount=Decimal("1000.00"), expense_date=date(2026, 4, 1),
        comment="", created_via="web", allow_negative=True,
    )
    assert e.pk is not None


@pytest.mark.django_db
def test_create_expense_custom_category():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000.00"), created_by=admin)
    e = create_expense(
        user=u, category=None, custom_name="Парковка",
        amount=Decimal("500.00"), expense_date=date(2026, 4, 1),
        comment="", created_via="web",
    )
    assert e.custom_category_name == "Парковка"


@pytest.mark.django_db
def test_create_expense_requires_category_xor_custom():
    u = UserFactory()
    with pytest.raises(ValueError):
        create_expense(
            user=u, category=None, custom_name="",
            amount=Decimal("100"), expense_date=date.today(),
            comment="", created_via="web", allow_negative=True,
        )


@pytest.mark.django_db
def test_create_expense_rejects_non_positive_amount():
    u = UserFactory()
    cat = CategoryFactory()
    with pytest.raises(ValueError):
        create_expense(
            user=u, category=cat, custom_name="",
            amount=Decimal("0"), expense_date=date.today(),
            comment="", created_via="web", allow_negative=True,
        )
```

- [ ] **Step 2: Run → FAIL**

```bash
POSTGRES_HOST=localhost pytest tests/test_expense_service.py -v
```

- [ ] **Step 3: Write `expenses/services/expenses.py`**

```python
from decimal import Decimal
from django.db import transaction
from expenses.models import Expense, AuditLog
from expenses.services.audit import write_audit
from expenses.services.balance import get_balance


class NegativeBalanceError(Exception):
    """Raised when the expense would take the balance negative and caller did not allow it."""
    def __init__(self, projected_balance: Decimal):
        self.projected_balance = projected_balance
        super().__init__(f"Баланс станет {projected_balance} ₸")


def create_expense(
    *,
    user,
    category,
    custom_name: str,
    amount: Decimal,
    expense_date,
    comment: str,
    created_via: str,
    allow_negative: bool = False,
):
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    if (category is None) == (custom_name == ""):
        raise ValueError("Укажите либо категорию, либо своё название")

    projected = get_balance(user) - amount
    if projected < 0 and not allow_negative:
        raise NegativeBalanceError(projected)

    with transaction.atomic():
        expense = Expense.objects.create(
            user=user,
            category=category,
            custom_category_name=custom_name,
            amount=amount,
            date=expense_date,
            comment=comment,
            created_via=created_via,
        )
        write_audit(
            user=user, action=AuditLog.ACTION_CREATE,
            entity=AuditLog.ENTITY_EXPENSE, entity_id=expense.id,
            diff={
                "amount": str(amount),
                "date": expense_date.isoformat(),
                "category_id": category.id if category else None,
                "custom_name": custom_name,
            },
        )
    return expense
```

- [ ] **Step 4: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_expense_service.py -v
```

Expected: all 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add expenses/services/expenses.py tests/test_expense_service.py
git commit -m "feat(expenses): add create_expense with negative balance guard"
```

---

## Task 15: expenses.update_expense + delete_expense (24h rule)

**Files:**
- Modify: `expenses/services/expenses.py`
- Test: `tests/test_expense_service.py`

- [ ] **Step 1: Append tests**

```python
from datetime import timedelta
from django.utils import timezone
from expenses.services.expenses import update_expense, delete_expense, EditWindowExpiredError


@pytest.mark.django_db
def test_update_expense_within_24h():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    e = create_expense(
        user=u, category=cat, custom_name="", amount=Decimal("1000"),
        expense_date=date.today(), comment="", created_via="web",
    )
    updated = update_expense(
        actor=u, expense=e, category=cat, custom_name="",
        amount=Decimal("1200"), expense_date=date.today(), comment="исправил",
    )
    assert updated.amount == Decimal("1200")
    assert updated.comment == "исправил"
    assert AuditLog.objects.filter(entity="expense", action="update").count() == 1


@pytest.mark.django_db
def test_update_expense_blocked_after_24h_for_owner():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    e = create_expense(
        user=u, category=cat, custom_name="", amount=Decimal("1000"),
        expense_date=date.today(), comment="", created_via="web",
    )
    # simulate aged record
    Expense.objects.filter(pk=e.pk).update(created_at=timezone.now() - timedelta(hours=25))
    e.refresh_from_db()
    with pytest.raises(EditWindowExpiredError):
        update_expense(
            actor=u, expense=e, category=cat, custom_name="",
            amount=Decimal("1200"), expense_date=date.today(), comment="",
        )


@pytest.mark.django_db
def test_admin_can_update_after_24h():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    e = create_expense(
        user=u, category=cat, custom_name="", amount=Decimal("1000"),
        expense_date=date.today(), comment="", created_via="web",
    )
    Expense.objects.filter(pk=e.pk).update(created_at=timezone.now() - timedelta(days=7))
    e.refresh_from_db()
    updated = update_expense(
        actor=admin, expense=e, category=cat, custom_name="",
        amount=Decimal("999"), expense_date=date.today(), comment="fix",
    )
    assert updated.amount == Decimal("999")


@pytest.mark.django_db
def test_delete_expense_soft_deletes_within_24h():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    e = create_expense(
        user=u, category=cat, custom_name="", amount=Decimal("1000"),
        expense_date=date.today(), comment="", created_via="web",
    )
    delete_expense(actor=u, expense=e)
    e.refresh_from_db()
    assert e.is_deleted
    assert AuditLog.objects.filter(entity="expense", action="delete").count() == 1
```

- [ ] **Step 2: Run → FAIL**

```bash
POSTGRES_HOST=localhost pytest tests/test_expense_service.py -v
```

- [ ] **Step 3: Append to `expenses/services/expenses.py`**

```python
from datetime import timedelta
from django.utils import timezone

EDIT_WINDOW = timedelta(hours=24)


class EditWindowExpiredError(Exception):
    pass


def _can_edit(actor, expense) -> bool:
    if getattr(actor, "is_admin", False):
        return True
    if actor.id != expense.user_id:
        return False
    age = timezone.now() - expense.created_at
    return age <= EDIT_WINDOW


def update_expense(*, actor, expense, category, custom_name, amount, expense_date, comment):
    if not _can_edit(actor, expense):
        raise EditWindowExpiredError("Редактирование недоступно (прошло больше 24 часов)")
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    if (category is None) == (custom_name == ""):
        raise ValueError("Укажите либо категорию, либо своё название")

    before = {
        "amount": str(expense.amount),
        "comment": expense.comment,
        "category_id": expense.category_id,
        "custom_name": expense.custom_category_name,
        "date": expense.date.isoformat(),
    }

    with transaction.atomic():
        expense.category = category
        expense.custom_category_name = custom_name
        expense.amount = amount
        expense.date = expense_date
        expense.comment = comment
        expense.save()
        write_audit(
            user=actor, action=AuditLog.ACTION_UPDATE,
            entity=AuditLog.ENTITY_EXPENSE, entity_id=expense.id,
            diff={"before": before, "after": {
                "amount": str(amount), "comment": comment,
                "category_id": category.id if category else None,
                "custom_name": custom_name, "date": expense_date.isoformat(),
            }},
        )
    return expense


def delete_expense(*, actor, expense):
    if not _can_edit(actor, expense):
        raise EditWindowExpiredError("Удаление недоступно (прошло больше 24 часов)")
    with transaction.atomic():
        expense.is_deleted = True
        expense.save(update_fields=["is_deleted", "updated_at"])
        write_audit(
            user=actor, action=AuditLog.ACTION_DELETE,
            entity=AuditLog.ENTITY_EXPENSE, entity_id=expense.id,
            diff={"amount": str(expense.amount)},
        )
```

- [ ] **Step 4: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_expense_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add expenses/services/expenses.py tests/test_expense_service.py
git commit -m "feat(expenses): add update/delete_expense with 24h edit window"
```

---

## Task 16: ExpenseForm

**Files:**
- Create: `expenses/forms.py`
- Test: `tests/test_forms.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_forms.py
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.factories import CategoryFactory
from expenses.forms import ExpenseForm


@pytest.mark.django_db
def test_expense_form_valid_with_category():
    cat = CategoryFactory()
    form = ExpenseForm(data={
        "category": cat.id, "custom_category_name": "",
        "amount": "1500.00", "date": date.today().isoformat(),
        "comment": "",
    })
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_expense_form_valid_with_custom_name():
    form = ExpenseForm(data={
        "category": "", "custom_category_name": "Парковка",
        "amount": "500.00", "date": date.today().isoformat(),
        "comment": "",
    })
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_expense_form_rejects_both_empty():
    form = ExpenseForm(data={
        "category": "", "custom_category_name": "",
        "amount": "500", "date": date.today().isoformat(),
    })
    assert not form.is_valid()


@pytest.mark.django_db
def test_expense_form_rejects_future_date():
    cat = CategoryFactory()
    form = ExpenseForm(data={
        "category": cat.id, "custom_category_name": "",
        "amount": "500", "date": (date.today() + timedelta(days=1)).isoformat(),
    })
    assert not form.is_valid()


@pytest.mark.django_db
def test_expense_form_rejects_very_old_date():
    cat = CategoryFactory()
    form = ExpenseForm(data={
        "category": cat.id, "custom_category_name": "",
        "amount": "500",
        "date": (date.today() - timedelta(days=365 * 3)).isoformat(),
    })
    assert not form.is_valid()
```

- [ ] **Step 2: Run → FAIL**

```bash
POSTGRES_HOST=localhost pytest tests/test_forms.py -v
```

- [ ] **Step 3: Write `expenses/forms.py`**

```python
from datetime import date, timedelta
from django import forms
from expenses.models import ExpenseCategory


class ExpenseForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.filter(is_active=True),
        required=False, empty_label="— выберите —", label="Категория",
    )
    custom_category_name = forms.CharField(
        max_length=64, required=False, label="Или введите своё",
    )
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0.01, label="Сумма (₸)",
    )
    date = forms.DateField(label="Дата", widget=forms.DateInput(attrs={"type": "date"}))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Комментарий")
    confirm_negative = forms.BooleanField(required=False, widget=forms.HiddenInput)

    def clean(self):
        cleaned = super().clean()
        cat = cleaned.get("category")
        custom = (cleaned.get("custom_category_name") or "").strip()
        if (cat is None) == (custom == ""):
            raise forms.ValidationError("Выберите категорию или введите своё название")
        cleaned["custom_category_name"] = custom
        return cleaned

    def clean_date(self):
        d = self.cleaned_data["date"]
        today = date.today()
        if d > today:
            raise forms.ValidationError("Дата не может быть в будущем")
        if d < today - timedelta(days=365 * 2):
            raise forms.ValidationError("Дата слишком старая (старше 2 лет)")
        return d
```

- [ ] **Step 4: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_forms.py -v
```

- [ ] **Step 5: Commit**

```bash
git add expenses/forms.py tests/test_forms.py
git commit -m "feat(expenses): add ExpenseForm with validation"
```

---

## Task 17: Cabinet view (balance + add button)

**Files:**
- Create: `expenses/views.py`, `expenses/urls.py`, `templates/expenses/cabinet.html`
- Modify: `config/urls.py`
- Test: `tests/test_views_cabinet.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_views_cabinet.py
from decimal import Decimal
import pytest
from django.urls import reverse
from tests.factories import UserFactory, AdminFactory, TopupFactory


@pytest.mark.django_db
def test_cabinet_requires_login(client):
    resp = client.get("/cabinet/")
    assert resp.status_code == 302
    assert "/login/" in resp["Location"]


@pytest.mark.django_db
def test_cabinet_shows_balance(client):
    u = UserFactory(username="alice")
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("50000.00"), created_by=admin)
    client.force_login(u)
    resp = client.get("/cabinet/")
    assert resp.status_code == 200
    assert b"50000" in resp.content
```

- [ ] **Step 2: Run → FAIL**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_cabinet.py -v
```

- [ ] **Step 3: Write `expenses/views.py`**

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from expenses.models import Expense, Topup
from expenses.services.balance import get_balance


@login_required
def cabinet(request):
    balance = get_balance(request.user)
    recent_expenses = Expense.objects.filter(
        user=request.user, is_deleted=False
    ).select_related("category")[:10]
    recent_topups = Topup.objects.filter(user=request.user)[:5]
    return render(request, "expenses/cabinet.html", {
        "balance": balance,
        "recent_expenses": recent_expenses,
        "recent_topups": recent_topups,
    })
```

- [ ] **Step 4: Write `expenses/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path("cabinet/", views.cabinet, name="cabinet"),
]
```

- [ ] **Step 5: Modify `config/urls.py`** to include expenses urls

```python
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("expenses.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 6: Write `templates/expenses/cabinet.html`**

```html
{% extends "base.html" %}
{% block title %}Кабинет — ManyTracker{% endblock %}
{% block content %}
<h1>Мой баланс</h1>
<div class="balance {% if balance < 0 %}negative{% endif %}">
  {{ balance }} ₸
</div>
{% if balance < 0 %}
  <p class="errors">Ваш баланс отрицательный — вам должны {{ balance|cut:"-" }} ₸.</p>
{% endif %}

<p><a href="{% url 'expense_create' %}"><button type="button">Добавить трату</button></a></p>

<h2>Последние траты</h2>
{% if recent_expenses %}
<table>
  <thead><tr><th>Дата</th><th>Категория</th><th>Сумма</th><th></th></tr></thead>
  <tbody>
  {% for e in recent_expenses %}
    <tr>
      <td>{{ e.date }}</td>
      <td>{{ e.category_display }}</td>
      <td>−{{ e.amount }} ₸</td>
      <td><a href="{% url 'expense_detail' e.id %}">подробнее</a></td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p>Пока ничего нет.</p>
{% endif %}
{% endblock %}
```

Note: template references `expense_create` and `expense_detail` URLs — they get added in the next task. To make this task's tests pass, temporarily change those to plain strings if the template fails to render. Safer: add empty placeholder urls now:

Modify `expenses/urls.py` to:

```python
from django.urls import path
from . import views

urlpatterns = [
    path("cabinet/", views.cabinet, name="cabinet"),
    path("expenses/new/", views.cabinet, name="expense_create"),   # placeholder
    path("expenses/<int:pk>/", views.cabinet, name="expense_detail"),  # placeholder
]
```

These are replaced properly in Task 18 and Task 19.

- [ ] **Step 7: Run tests → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_cabinet.py -v
```

- [ ] **Step 8: Commit**

```bash
git add expenses/views.py expenses/urls.py config/urls.py templates/expenses/cabinet.html tests/test_views_cabinet.py
git commit -m "feat(expenses): add cabinet view showing balance and recent history"
```

---

## Task 18: Expense create view (with negative confirm flow)

**Files:**
- Modify: `expenses/views.py`, `expenses/urls.py`
- Create: `templates/expenses/expense_form.html`
- Test: `tests/test_views_expense.py`

- [ ] **Step 1: Write failing test `tests/test_views_expense.py`**

```python
from decimal import Decimal
from datetime import date
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory, CategoryFactory
from expenses.models import Expense


@pytest.mark.django_db
def test_create_expense_happy_path(client):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u)
    resp = client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1500.00", "date": date.today().isoformat(), "comment": "обед",
    })
    assert resp.status_code == 302
    assert Expense.objects.filter(user=u).count() == 1


@pytest.mark.django_db
def test_create_expense_shows_negative_warning(client):
    u = UserFactory()
    cat = CategoryFactory()
    client.force_login(u)
    resp = client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000.00", "date": date.today().isoformat(), "comment": "",
    })
    assert resp.status_code == 200  # stays on form
    assert b"Баланс станет" in resp.content
    assert Expense.objects.count() == 0


@pytest.mark.django_db
def test_create_expense_confirm_negative(client):
    u = UserFactory()
    cat = CategoryFactory()
    client.force_login(u)
    resp = client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000.00", "date": date.today().isoformat(), "comment": "",
        "confirm_negative": "on",
    })
    assert resp.status_code == 302
    assert Expense.objects.count() == 1
```

- [ ] **Step 2: Run → FAIL**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_expense.py -v
```

- [ ] **Step 3: Add `expense_create` to `expenses/views.py`**

Replace `expenses/views.py` with:

```python
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from expenses.forms import ExpenseForm
from expenses.models import Expense, ExpenseAttachment, Topup
from expenses.services.balance import get_balance
from expenses.services.expenses import (
    NegativeBalanceError,
    create_expense,
)


@login_required
def cabinet(request):
    balance = get_balance(request.user)
    recent_expenses = Expense.objects.filter(
        user=request.user, is_deleted=False
    ).select_related("category")[:10]
    recent_topups = Topup.objects.filter(user=request.user)[:5]
    return render(request, "expenses/cabinet.html", {
        "balance": balance,
        "recent_expenses": recent_expenses,
        "recent_topups": recent_topups,
    })


@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)
    warning = None
    if request.method == "POST" and form.is_valid():
        try:
            expense = create_expense(
                user=request.user,
                category=form.cleaned_data["category"],
                custom_name=form.cleaned_data["custom_category_name"],
                amount=form.cleaned_data["amount"],
                expense_date=form.cleaned_data["date"],
                comment=form.cleaned_data["comment"],
                created_via="web",
                allow_negative=form.cleaned_data.get("confirm_negative", False),
            )
        except NegativeBalanceError as exc:
            warning = f"Баланс станет {exc.projected_balance} ₸. Продолжить?"
            form.fields["confirm_negative"].widget = form.fields["confirm_negative"].widget.__class__()
            form.initial["confirm_negative"] = True
        else:
            for f in request.FILES.getlist("attachments"):
                ExpenseAttachment.objects.create(
                    expense=expense, file=f,
                    original_name=f.name, mime_type=f.content_type or "",
                    size=f.size,
                )
            messages.success(request, "Трата добавлена")
            return redirect("cabinet")
    return render(request, "expenses/expense_form.html", {"form": form, "warning": warning})
```

- [ ] **Step 4: Update `expenses/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path("cabinet/", views.cabinet, name="cabinet"),
    path("expenses/new/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/", views.cabinet, name="expense_detail"),  # placeholder until Task 19
]
```

- [ ] **Step 5: Write `templates/expenses/expense_form.html`**

```html
{% extends "base.html" %}
{% block title %}Добавить трату{% endblock %}
{% block content %}
<h1>Добавить трату</h1>
{% if warning %}
  <div class="errors">{{ warning }}</div>
{% endif %}
<form method="post" enctype="multipart/form-data">
  {% csrf_token %}
  {% if form.non_field_errors %}<div class="errors">{{ form.non_field_errors }}</div>{% endif %}
  <label>{{ form.category.label }}</label>
  {{ form.category }}
  {{ form.category.errors }}

  <label>{{ form.custom_category_name.label }}</label>
  {{ form.custom_category_name }}
  {{ form.custom_category_name.errors }}

  <label>{{ form.amount.label }}</label>
  {{ form.amount }}
  {{ form.amount.errors }}

  <label>{{ form.date.label }}</label>
  {{ form.date }}
  {{ form.date.errors }}

  <label>{{ form.comment.label }}</label>
  {{ form.comment }}

  <label>Файлы (до 10 МБ каждый)</label>
  <input type="file" name="attachments" multiple>

  {% if warning %}
    <input type="hidden" name="confirm_negative" value="on">
  {% endif %}

  <button type="submit">{% if warning %}Подтвердить{% else %}Сохранить{% endif %}</button>
  <a href="{% url 'cabinet' %}">Отмена</a>
</form>
{% endblock %}
```

- [ ] **Step 6: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_expense.py -v
```

- [ ] **Step 7: Commit**

```bash
git add expenses/views.py expenses/urls.py templates/expenses/expense_form.html tests/test_views_expense.py
git commit -m "feat(expenses): add expense create view with negative-balance confirm"
```

---

## Task 19: Expense detail / edit / delete views

**Files:**
- Modify: `expenses/views.py`, `expenses/urls.py`
- Create: `templates/expenses/expense_detail.html`, `templates/expenses/confirm_delete.html`
- Test: `tests/test_views_expense.py` (append)

- [ ] **Step 1: Append failing tests**

```python
from datetime import timedelta
from django.utils import timezone


@pytest.mark.django_db
def test_owner_can_edit_within_24h(client):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u)
    client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000", "date": date.today().isoformat(), "comment": "",
    })
    expense = Expense.objects.get(user=u)
    resp = client.post(f"/expenses/{expense.id}/edit/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1200", "date": date.today().isoformat(), "comment": "fix",
    })
    assert resp.status_code == 302
    expense.refresh_from_db()
    assert expense.amount == Decimal("1200")


@pytest.mark.django_db
def test_owner_cannot_edit_others(client):
    u1 = UserFactory()
    u2 = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u1, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u1)
    client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000", "date": date.today().isoformat(), "comment": "",
    })
    expense = Expense.objects.get(user=u1)
    client.force_login(u2)
    resp = client.get(f"/expenses/{expense.id}/edit/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_owner_cannot_edit_after_24h(client):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u)
    client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000", "date": date.today().isoformat(), "comment": "",
    })
    expense = Expense.objects.get(user=u)
    Expense.objects.filter(pk=expense.pk).update(
        created_at=timezone.now() - timedelta(hours=25)
    )
    resp = client.post(f"/expenses/{expense.id}/edit/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1200", "date": date.today().isoformat(),
    })
    assert resp.status_code == 403


@pytest.mark.django_db
def test_delete_soft_deletes(client):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u)
    client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000", "date": date.today().isoformat(), "comment": "",
    })
    expense = Expense.objects.get(user=u)
    resp = client.post(f"/expenses/{expense.id}/delete/")
    assert resp.status_code == 302
    expense.refresh_from_db()
    assert expense.is_deleted
```

- [ ] **Step 2: Run → FAIL**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_expense.py -v
```

- [ ] **Step 3: Add to `expenses/views.py`**

```python
from django.http import HttpResponseForbidden
from expenses.services.expenses import (
    update_expense, delete_expense, EditWindowExpiredError,
)


def _get_own_expense(request, pk):
    qs = Expense.objects.filter(is_deleted=False)
    if not request.user.is_admin:
        qs = qs.filter(user=request.user)
    return get_object_or_404(qs, pk=pk)


@login_required
def expense_detail(request, pk):
    expense = _get_own_expense(request, pk)
    return render(request, "expenses/expense_detail.html", {"expense": expense})


@login_required
def expense_edit(request, pk):
    expense = _get_own_expense(request, pk)
    form = ExpenseForm(request.POST or None, initial={
        "category": expense.category_id,
        "custom_category_name": expense.custom_category_name,
        "amount": expense.amount,
        "date": expense.date,
        "comment": expense.comment,
    })
    if request.method == "POST" and form.is_valid():
        try:
            update_expense(
                actor=request.user,
                expense=expense,
                category=form.cleaned_data["category"],
                custom_name=form.cleaned_data["custom_category_name"],
                amount=form.cleaned_data["amount"],
                expense_date=form.cleaned_data["date"],
                comment=form.cleaned_data["comment"],
            )
        except EditWindowExpiredError as exc:
            return HttpResponseForbidden(str(exc))
        messages.success(request, "Трата обновлена")
        return redirect("cabinet")
    return render(request, "expenses/expense_form.html", {
        "form": form, "warning": None, "edit_mode": True, "expense": expense,
    })


@login_required
def expense_delete(request, pk):
    expense = _get_own_expense(request, pk)
    if request.method == "POST":
        try:
            delete_expense(actor=request.user, expense=expense)
        except EditWindowExpiredError as exc:
            return HttpResponseForbidden(str(exc))
        messages.success(request, "Трата удалена")
        return redirect("cabinet")
    return render(request, "expenses/confirm_delete.html", {"expense": expense})
```

- [ ] **Step 4: Update `expenses/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path("cabinet/", views.cabinet, name="cabinet"),
    path("expenses/new/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/", views.expense_detail, name="expense_detail"),
    path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
]
```

- [ ] **Step 5: Create `templates/expenses/expense_detail.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Трата #{{ expense.id }}</h1>
<p><strong>Дата:</strong> {{ expense.date }}</p>
<p><strong>Категория:</strong> {{ expense.category_display }}</p>
<p><strong>Сумма:</strong> {{ expense.amount }} ₸</p>
<p><strong>Комментарий:</strong> {{ expense.comment|default:"—" }}</p>

<h3>Файлы</h3>
<ul>
{% for a in expense.attachments.all %}
  <li><a href="{% url 'attachment_download' a.id %}">{{ a.original_name }}</a></li>
{% empty %}
  <li>нет</li>
{% endfor %}
</ul>

<p>
  <a href="{% url 'expense_edit' expense.id %}">Редактировать</a> |
  <a href="{% url 'expense_delete' expense.id %}">Удалить</a> |
  <a href="{% url 'cabinet' %}">← назад</a>
</p>
{% endblock %}
```

- [ ] **Step 6: Create `templates/expenses/confirm_delete.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Удалить трату?</h1>
<p>{{ expense.date }} — {{ expense.category_display }} — {{ expense.amount }} ₸</p>
<form method="post">
  {% csrf_token %}
  <button type="submit">Да, удалить</button>
  <a href="{% url 'expense_detail' expense.id %}">Отмена</a>
</form>
{% endblock %}
```

- [ ] **Step 7: Add placeholder `attachment_download` URL** (real one in Task 21)

In `expenses/urls.py`, append:

```python
    path("attachments/<int:pk>/", views.cabinet, name="attachment_download"),  # placeholder
```

- [ ] **Step 8: Run tests → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_expense.py -v
```

- [ ] **Step 9: Commit**

```bash
git add expenses/views.py expenses/urls.py templates/expenses/
git commit -m "feat(expenses): add expense detail, edit, and delete views"
```

---

## Task 20: History view with date filter

**Files:**
- Modify: `expenses/views.py`, `expenses/urls.py`
- Create: `templates/expenses/history.html`
- Test: `tests/test_views_history.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_views_history.py
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory, ExpenseFactory, CategoryFactory


@pytest.mark.django_db
def test_history_shows_own_expenses_only(client):
    u1 = UserFactory()
    u2 = UserFactory()
    cat = CategoryFactory(name="Такси")
    ExpenseFactory(user=u1, amount=Decimal("1000"), category=cat)
    ExpenseFactory(user=u2, amount=Decimal("9999"), category=cat)
    client.force_login(u1)
    resp = client.get("/history/")
    assert resp.status_code == 200
    assert b"1000" in resp.content
    assert b"9999" not in resp.content


@pytest.mark.django_db
def test_history_filters_by_date_range(client):
    u = UserFactory()
    cat = CategoryFactory()
    ExpenseFactory(user=u, amount=Decimal("1111"), date=date(2026, 1, 1), category=cat)
    ExpenseFactory(user=u, amount=Decimal("2222"), date=date(2026, 4, 1), category=cat)
    client.force_login(u)
    resp = client.get("/history/?from=2026-03-01&to=2026-04-30")
    assert b"2222" in resp.content
    assert b"1111" not in resp.content
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Add to `expenses/views.py`**

```python
from datetime import date as date_cls, datetime


@login_required
def history(request):
    qs = Expense.objects.filter(user=request.user, is_deleted=False).select_related("category")
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    if date_from:
        try:
            qs = qs.filter(date__gte=datetime.strptime(date_from, "%Y-%m-%d").date())
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(date__lte=datetime.strptime(date_to, "%Y-%m-%d").date())
        except ValueError:
            pass
    topups = Topup.objects.filter(user=request.user)
    return render(request, "expenses/history.html", {
        "expenses": qs, "topups": topups,
        "date_from": date_from, "date_to": date_to,
    })
```

- [ ] **Step 4: Update `expenses/urls.py`**

Add:

```python
    path("history/", views.history, name="history"),
```

- [ ] **Step 5: Write `templates/expenses/history.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>История</h1>
<form method="get">
  <label>С</label>
  <input type="date" name="from" value="{{ date_from|default:'' }}">
  <label>По</label>
  <input type="date" name="to" value="{{ date_to|default:'' }}">
  <button type="submit">Фильтр</button>
</form>

<h2>Траты</h2>
<table>
  <thead><tr><th>Дата</th><th>Категория</th><th>Сумма</th><th>Комментарий</th></tr></thead>
  <tbody>
  {% for e in expenses %}
    <tr>
      <td>{{ e.date }}</td>
      <td>{{ e.category_display }}</td>
      <td>−{{ e.amount }} ₸</td>
      <td>{{ e.comment|truncatechars:50 }}</td>
    </tr>
  {% empty %}
    <tr><td colspan="4">Нет данных</td></tr>
  {% endfor %}
  </tbody>
</table>

<h2>Пополнения</h2>
<table>
  <thead><tr><th>Дата</th><th>Сумма</th><th>Комментарий</th></tr></thead>
  <tbody>
  {% for t in topups %}
    <tr><td>{{ t.date }}</td><td>+{{ t.amount }} ₸</td><td>{{ t.comment }}</td></tr>
  {% empty %}
    <tr><td colspan="3">Нет данных</td></tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 6: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_history.py -v
```

- [ ] **Step 7: Commit**

```bash
git add expenses/views.py expenses/urls.py templates/expenses/history.html tests/test_views_history.py
git commit -m "feat(expenses): add history view with date range filter"
```

---

## Task 21: Secure file download view

**Files:**
- Modify: `expenses/views.py`, `expenses/urls.py`
- Test: `tests/test_file_download.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_file_download.py
from decimal import Decimal
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from tests.factories import UserFactory, AdminFactory, CategoryFactory, TopupFactory
from expenses.models import Expense, ExpenseAttachment


@pytest.fixture
def expense_with_file(db):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    e = Expense.objects.create(user=u, category=cat, amount=Decimal("500"), date="2026-04-01")
    f = SimpleUploadedFile("chek.pdf", b"PDFDATA", content_type="application/pdf")
    att = ExpenseAttachment.objects.create(
        expense=e, file=f, original_name="chek.pdf",
        mime_type="application/pdf", size=7,
    )
    return u, att


@pytest.mark.django_db
def test_owner_can_download(client, expense_with_file):
    u, att = expense_with_file
    client.force_login(u)
    resp = client.get(f"/attachments/{att.id}/")
    assert resp.status_code == 200
    assert b"PDFDATA" in b"".join(resp.streaming_content) if resp.streaming_content else resp.content


@pytest.mark.django_db
def test_other_user_cannot_download(client, expense_with_file):
    _, att = expense_with_file
    other = UserFactory()
    client.force_login(other)
    resp = client.get(f"/attachments/{att.id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_admin_can_download(client, expense_with_file):
    _, att = expense_with_file
    admin = AdminFactory()
    client.force_login(admin)
    resp = client.get(f"/attachments/{att.id}/")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Add to `expenses/views.py`**

```python
from django.http import FileResponse
from expenses.models import ExpenseAttachment


@login_required
def attachment_download(request, pk):
    qs = ExpenseAttachment.objects.select_related("expense")
    if not request.user.is_admin:
        qs = qs.filter(expense__user=request.user)
    att = get_object_or_404(qs, pk=pk)
    return FileResponse(
        att.file.open("rb"),
        as_attachment=True,
        filename=att.original_name,
        content_type=att.mime_type or "application/octet-stream",
    )
```

- [ ] **Step 4: Replace placeholder in `expenses/urls.py`**

```python
    path("attachments/<int:pk>/", views.attachment_download, name="attachment_download"),
```

- [ ] **Step 5: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_file_download.py -v
```

- [ ] **Step 6: Commit**

```bash
git add expenses/views.py expenses/urls.py tests/test_file_download.py
git commit -m "feat(expenses): add secure attachment download view"
```

---

## Task 22: Django admin — Users with balance column

**Files:**
- Modify: `accounts/admin.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write failing test `tests/test_admin.py`**

```python
from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory


@pytest.mark.django_db
def test_admin_users_list_shows_balance(client):
    admin = AdminFactory()
    u = UserFactory(username="alice")
    TopupFactory(user=u, amount=Decimal("12345.00"), created_by=admin)
    client.force_login(admin)
    resp = client.get("/admin/accounts/user/")
    assert resp.status_code == 200
    assert b"12345" in resp.content
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Write `accounts/admin.py`**

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm

from expenses.services.balance import get_balance
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "full_name", "is_admin", "is_active", "balance_display")
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

    def balance_display(self, obj):
        return f"{get_balance(obj)} ₸"
    balance_display.short_description = "Баланс"
```

- [ ] **Step 4: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_admin.py -v
```

- [ ] **Step 5: Commit**

```bash
git add accounts/admin.py tests/test_admin.py
git commit -m "feat(accounts): add admin list with balance column"
```

---

## Task 23: Django admin — Categories, Topups, Expenses, AuditLog

**Files:**
- Modify: `expenses/admin.py`
- Test: `tests/test_admin.py` (append)

- [ ] **Step 1: Append test**

```python
@pytest.mark.django_db
def test_admin_expenses_list(client):
    admin = AdminFactory()
    u = UserFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    from tests.factories import ExpenseFactory, CategoryFactory
    cat = CategoryFactory(name="Такси")
    ExpenseFactory(user=u, amount=Decimal("2500"), category=cat)
    client.force_login(admin)
    resp = client.get("/admin/expenses/expense/")
    assert resp.status_code == 200
    assert b"2500" in resp.content
    assert b"alice" in resp.content or b"user" in resp.content
```

- [ ] **Step 2: Write `expenses/admin.py`**

```python
import csv
from django.contrib import admin
from django.http import HttpResponse

from .models import ExpenseCategory, Topup, Expense, ExpenseAttachment, AuditLog


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name",)


@admin.register(Topup)
class TopupAdmin(admin.ModelAdmin):
    list_display = ("date", "user", "amount", "comment", "created_by", "created_at")
    list_filter = ("user", "date")
    search_fields = ("comment",)
    date_hierarchy = "date"

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class ExpenseAttachmentInline(admin.TabularInline):
    model = ExpenseAttachment
    extra = 0
    readonly_fields = ("original_name", "mime_type", "size", "uploaded_at")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "date", "user", "category", "custom_category_name",
        "amount", "comment_short", "created_via", "is_deleted", "created_at",
    )
    list_filter = ("user", "category", "created_via", "is_deleted", "date")
    search_fields = ("comment", "custom_category_name")
    date_hierarchy = "date"
    inlines = [ExpenseAttachmentInline]
    actions = ["export_as_csv"]

    def comment_short(self, obj):
        return (obj.comment or "")[:40]
    comment_short.short_description = "Комментарий"

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="expenses.csv"'
        writer = csv.writer(response)
        writer.writerow(["Дата", "Сотрудник", "Категория", "Сумма", "Комментарий", "Источник"])
        for e in queryset.select_related("user", "category"):
            writer.writerow([
                e.date, e.user.username,
                e.category.name if e.category else e.custom_category_name,
                e.amount, e.comment, e.created_via,
            ])
        return response
    export_as_csv.short_description = "Экспорт в CSV"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "entity", "entity_id")
    list_filter = ("action", "entity", "user")
    readonly_fields = ("user", "action", "entity", "entity_id", "diff", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

- [ ] **Step 3: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_admin.py -v
```

- [ ] **Step 4: Commit**

```bash
git add expenses/admin.py tests/test_admin.py
git commit -m "feat(expenses): register admin pages for categories, topups, expenses, audit log"
```

---

## Task 24: Permissions tests (defensive)

**Files:**
- Create: `tests/test_permissions.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from tests.factories import UserFactory, AdminFactory


@pytest.mark.django_db
def test_non_admin_cannot_access_admin_site(client):
    u = UserFactory()
    client.force_login(u)
    resp = client.get("/admin/")
    # Django redirects to admin login
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_admin_can_access_admin_site(client):
    admin = AdminFactory()
    client.force_login(admin)
    resp = client.get("/admin/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_anonymous_redirected_from_cabinet(client):
    resp = client.get("/cabinet/")
    assert resp.status_code == 302
    assert "/login/" in resp["Location"]


@pytest.mark.django_db
def test_anonymous_redirected_from_history(client):
    resp = client.get("/history/")
    assert resp.status_code == 302
```

- [ ] **Step 2: Run**

```bash
POSTGRES_HOST=localhost pytest tests/test_permissions.py -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_permissions.py
git commit -m "test: add permission tests for admin and anonymous access"
```

---

## Task 25: README and run instructions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
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
```

- [ ] **Step 2: Run full test suite**

```bash
POSTGRES_HOST=localhost pytest -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with local dev instructions"
```

---

## Task 26: End-to-end smoke flow (manual)

**Files:** none (manual verification)

- [ ] **Step 1: Fresh migrate + superuser**

```bash
POSTGRES_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost python manage.py createsuperuser
# username: boss, password: boss123456
```

- [ ] **Step 2: Run server**

```bash
POSTGRES_HOST=localhost python manage.py runserver
```

- [ ] **Step 3: In browser — admin flow**

1. Open http://localhost:8000/admin/ → login as `boss`
2. Create category "Такси", "Обед"
3. Create user `alice` with password `alicepass123`
4. Create topup for alice: 50000 KZT, today
5. Verify alice's balance column shows 50000 ₸

- [ ] **Step 4: Employee flow**

1. Log out, go to http://localhost:8000/login/
2. Login as `alice` → cabinet shows 50000 ₸
3. Add expense: category Такси, 1500, today, comment "аэропорт", attach a small PDF
4. Verify balance now 48500 ₸
5. Add expense that would go negative (e.g. 60000) → see warning → confirm → balance −11500
6. Open history → filter by last 30 days → both expenses visible
7. Try editing the first expense — should work
8. Try downloading the attached PDF — should download

- [ ] **Step 5: Audit check**

1. Back in admin as boss → AuditLog section → see create entries for both expenses and the topup

- [ ] **Step 6: If everything works, commit a marker**

```bash
git commit --allow-empty -m "chore: phase 1 MVP smoke test passed"
```

---

## Done Criteria

- [ ] All pytest tests pass
- [ ] Manual smoke flow in Task 26 passes
- [ ] `docker compose up` brings the stack up cleanly
- [ ] `docker compose exec web python manage.py migrate` works inside container
- [ ] Admin can create users, categories, topups; sees all expenses with filters and CSV export
- [ ] Employee can log in, add expense, attach file, edit/delete within 24 h, download own files
- [ ] Negative balance works with explicit confirmation
- [ ] AuditLog records create/update/delete for expenses and topups

---

## Self-Review notes

**Spec coverage:**
- Stack & architecture → Tasks 1-3, 25 ✓
- User model + login → Tasks 4, 6 ✓
- Category/Topup/Expense/Attachment/AuditLog models → Tasks 5, 7-10 ✓
- Balance service → Task 12 ✓
- Topup create service → Task 13 ✓
- Expense create with negative confirm → Task 14 ✓
- Expense edit/delete with 24h rule → Task 15 ✓
- ExpenseForm validation (xor, date window) → Task 16 ✓
- Cabinet view → Task 17 ✓
- Expense create view with confirm flow → Task 18 ✓
- Expense detail/edit/delete views + ownership → Task 19 ✓
- History with date filter → Task 20 ✓
- Secure file download → Task 21 ✓
- Django admin (Users with balance, Categories, Topups, Expenses with filters/CSV, AuditLog read-only) → Tasks 22-23 ✓
- Permissions → Task 24 ✓
- Tests for all services, forms, views, permissions ✓

**Out of scope for Phase 1 (will be separate plans):**
- Telegram bot (Phase 2)
- Admin dashboard custom page (Phase 3)
- Rate limiting via django-axes (Phase 3)
- nginx + TLS + backups production deploy (Phase 4)
