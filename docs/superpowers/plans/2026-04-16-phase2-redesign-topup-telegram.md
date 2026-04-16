# Phase 2: Redesign + Employee Topup + Telegram Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add employee self-topup, redesign the web cabinet with Wedrink-inspired mobile-first UI (teal/red palette, wallet-style income/expense), and build a Telegram bot for balance/expense/topup/history.

**Architecture:** Extends Phase 1 Django monolith. New `source` field on Topup model, new topup view/form for employees, full template redesign with CSS custom properties, new `bot/` Django app with python-telegram-bot running as a separate Docker service sharing the same DB and services layer.

**Tech Stack:** Phase 1 stack + python-telegram-bot==21.5, pytest-asyncio==0.23.8

**Spec:** `docs/superpowers/specs/2026-04-16-phase2-redesign-topup-telegram.md`

---

## File Structure (changes from Phase 1)

```
my-project/
├── requirements.txt                      # Task 1 — add python-telegram-bot, pytest-asyncio
├── docker-compose.yml                    # Task 14 — add bot service
├── .env.example                          # Task 14 — add TELEGRAM_BOT_TOKEN
├── config/settings.py                    # Task 13 — add "bot" to INSTALLED_APPS
├── expenses/
│   ├── models.py                         # Task 1 — Topup.source field
│   ├── services/topups.py                # Task 2 — source param
│   ├── admin.py                          # Task 5 — source column/filter
│   ├── forms.py                          # Task 3 — EmployeeTopupForm
│   ├── views.py                          # Task 4, 7, 10, 11 — topup_create, redesigned views
│   └── urls.py                           # Task 4 — topup_create route
├── templates/
│   ├── base.html                         # Task 6 — full redesign
│   ├── accounts/login.html               # Task 6 — redesigned
│   └── expenses/
│       ├── cabinet.html                  # Task 7 — wallet-style redesign
│       ├── expense_form.html             # Task 8 — redesigned
│       ├── topup_form.html               # Task 9 — new
│       ├── history.html                  # Task 10 — unified timeline
│       ├── expense_detail.html           # Task 8 — redesigned
│       ├── confirm_delete.html           # Task 8 — redesigned
│       └── profile.html                  # Task 11 — new
├── static/
│   └── css/style.css                     # Task 6 — design system CSS
├── bot/                                  # Tasks 13-20
│   ├── __init__.py
│   ├── apps.py
│   ├── management/commands/run_bot.py    # Task 13
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py                      # Task 15
│   │   ├── menu.py                       # Task 16
│   │   ├── balance.py                    # Task 17
│   │   ├── add_expense.py                # Task 18
│   │   ├── add_topup.py                  # Task 19
│   │   └── history.py                    # Task 20
│   └── keyboards.py                      # Task 16
└── tests/
    ├── test_topup_employee.py            # Task 2
    ├── test_topup_form.py                # Task 3
    ├── test_views_topup.py               # Task 4
    ├── test_bot_start.py                 # Task 15
    ├── test_bot_balance.py               # Task 17
    ├── test_bot_expense.py               # Task 18
    ├── test_bot_topup.py                 # Task 19
    └── test_bot_history.py               # Task 20
```

---

# Part A: Employee Topup (Tasks 1–5)

---

### Task 1: Add `source` field to Topup model

**Files:**
- Modify: `expenses/models.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add `source` field to Topup in `expenses/models.py`**

After `created_at` field (line 38), add:

```python
    SOURCE_ADMIN = "admin"
    SOURCE_EMPLOYEE = "employee"
    SOURCE_CHOICES = [
        (SOURCE_ADMIN, "Админ"),
        (SOURCE_EMPLOYEE, "Сотрудник"),
    ]
```

Move these constants ABOVE the field definitions (after `class Topup(models.Model):`), then add the field after `created_at`:

```python
    source = models.CharField(
        max_length=16, choices=SOURCE_CHOICES, default=SOURCE_ADMIN,
    )
```

- [ ] **Step 2: Add python-telegram-bot and pytest-asyncio to `requirements.txt`**

Append:

```
python-telegram-bot==21.5
pytest-asyncio==0.23.8
```

- [ ] **Step 3: Install new deps**

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 4: Make migration**

```bash
python manage.py makemigrations expenses
```

Expected: migration adding `source` field with default `"admin"`.

- [ ] **Step 5: Run migration**

```bash
POSTGRES_HOST=localhost python manage.py migrate
```

- [ ] **Step 6: Verify existing tests still pass**

```bash
POSTGRES_HOST=localhost pytest -v
```

Expected: all 50 tests PASS (source has default, backward compatible).

- [ ] **Step 7: Commit**

```bash
git add requirements.txt expenses/models.py expenses/migrations/
git commit -m "feat(expenses): add source field to Topup model"
```

---

### Task 2: Update create_topup service + test employee topup

**Files:**
- Modify: `expenses/services/topups.py`
- Create: `tests/test_topup_employee.py`

- [ ] **Step 1: Write failing test `tests/test_topup_employee.py`**

```python
from datetime import date
from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory
from expenses.services.topups import create_topup
from expenses.models import Topup, AuditLog


@pytest.mark.django_db
def test_create_topup_from_admin():
    u = UserFactory()
    admin = AdminFactory()
    topup = create_topup(
        created_by=admin, user=u, amount=Decimal("50000.00"),
        topup_date=date(2026, 4, 1), comment="Аванс", source="admin",
    )
    assert topup.source == "admin"
    assert topup.created_by == admin


@pytest.mark.django_db
def test_create_topup_from_employee():
    u = UserFactory()
    topup = create_topup(
        created_by=u, user=u, amount=Decimal("10000.00"),
        topup_date=date(2026, 4, 10), comment="Получил от Серика",
        source="employee",
    )
    assert topup.source == "employee"
    assert topup.created_by == u
    assert topup.user == u
    assert AuditLog.objects.filter(entity="topup", action="create").count() == 1


@pytest.mark.django_db
def test_employee_topup_requires_comment():
    u = UserFactory()
    with pytest.raises(ValueError, match="Комментарий"):
        create_topup(
            created_by=u, user=u, amount=Decimal("5000"),
            topup_date=date.today(), comment="", source="employee",
        )
```

- [ ] **Step 2: Run → FAIL** (old signature uses `admin=` param)

```bash
source .venv/bin/activate
POSTGRES_HOST=localhost pytest tests/test_topup_employee.py -v
```

- [ ] **Step 3: Rewrite `expenses/services/topups.py`**

```python
from decimal import Decimal
from django.db import transaction
from expenses.models import Topup, AuditLog
from expenses.services.audit import write_audit


def create_topup(*, created_by, user, amount: Decimal, topup_date, comment: str = "", source: str = "admin"):
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    if source == "employee" and not comment.strip():
        raise ValueError("Комментарий обязателен для пополнения от сотрудника")
    with transaction.atomic():
        topup = Topup.objects.create(
            user=user, amount=amount, date=topup_date, comment=comment,
            created_by=created_by, source=source,
        )
        write_audit(
            user=created_by, action=AuditLog.ACTION_CREATE,
            entity=AuditLog.ENTITY_TOPUP, entity_id=topup.id,
            diff={
                "amount": str(amount), "user_id": user.id,
                "date": topup_date.isoformat(), "source": source,
            },
        )
    return topup
```

- [ ] **Step 4: Fix existing callers**

The old signature used `admin=` keyword. Now it's `created_by=`. Update:

In `expenses/admin.py`, find `TopupAdmin.save_model` — if it calls `create_topup`, update the keyword. (Currently it uses Django's default save, so no change needed.)

In `tests/test_topup_service.py`, update existing tests: replace `admin=admin` with `created_by=admin`.

In `tests/factories.py`, `TopupFactory` uses `created_by` field directly on the model (not the service), so no change needed.

- [ ] **Step 5: Run all tests**

```bash
POSTGRES_HOST=localhost pytest -v
```

Expected: all old tests PASS + 3 new PASS = 53 total.

- [ ] **Step 6: Commit**

```bash
git add expenses/services/topups.py tests/test_topup_employee.py tests/test_topup_service.py
git commit -m "feat(expenses): update create_topup with source param and employee validation"
```

---

### Task 3: EmployeeTopupForm

**Files:**
- Modify: `expenses/forms.py`
- Create: `tests/test_topup_form.py`

- [ ] **Step 1: Write failing test `tests/test_topup_form.py`**

```python
from datetime import date, timedelta
import pytest
from expenses.forms import EmployeeTopupForm


def test_topup_form_valid():
    form = EmployeeTopupForm(data={
        "amount": "10000.00",
        "date": date.today().isoformat(),
        "comment": "Получил от Серика",
    })
    assert form.is_valid(), form.errors


def test_topup_form_requires_comment():
    form = EmployeeTopupForm(data={
        "amount": "10000.00",
        "date": date.today().isoformat(),
        "comment": "",
    })
    assert not form.is_valid()
    assert "comment" in form.errors


def test_topup_form_rejects_future_date():
    form = EmployeeTopupForm(data={
        "amount": "10000.00",
        "date": (date.today() + timedelta(days=1)).isoformat(),
        "comment": "test",
    })
    assert not form.is_valid()


def test_topup_form_rejects_zero_amount():
    form = EmployeeTopupForm(data={
        "amount": "0",
        "date": date.today().isoformat(),
        "comment": "test",
    })
    assert not form.is_valid()
```

- [ ] **Step 2: Run → FAIL**

```bash
source .venv/bin/activate
POSTGRES_HOST=localhost pytest tests/test_topup_form.py -v
```

- [ ] **Step 3: Append `EmployeeTopupForm` to `expenses/forms.py`**

```python
class EmployeeTopupForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0.01, label="Сумма (₸)",
    )
    date = forms.DateField(label="Дата", widget=forms.DateInput(attrs={"type": "date"}))
    comment = forms.CharField(
        max_length=256, label="Комментарий (от кого / за что)",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean_date(self):
        d = self.cleaned_data["date"]
        today = date.today()
        if d > today:
            raise forms.ValidationError("Дата не может быть в будущем")
        if d < today - timedelta(days=365 * 2):
            raise forms.ValidationError("Дата слишком старая (старше 2 лет)")
        return d
```

Add `from datetime import date, timedelta` at the top of `expenses/forms.py` if not already there.

- [ ] **Step 4: Run → PASS (4)**

```bash
POSTGRES_HOST=localhost pytest tests/test_topup_form.py -v
```

- [ ] **Step 5: Commit**

```bash
git add expenses/forms.py tests/test_topup_form.py
git commit -m "feat(expenses): add EmployeeTopupForm with comment validation"
```

---

### Task 4: Employee topup view

**Files:**
- Modify: `expenses/views.py`, `expenses/urls.py`
- Create: `tests/test_views_topup.py`

- [ ] **Step 1: Write failing test `tests/test_views_topup.py`**

```python
from decimal import Decimal
from datetime import date
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory
from expenses.models import Topup
from expenses.services.balance import get_balance


@pytest.mark.django_db
def test_topup_create_requires_login(client):
    resp = client.get("/topup/new/")
    assert resp.status_code == 302
    assert "/login/" in resp["Location"]


@pytest.mark.django_db
def test_topup_create_happy_path(client):
    u = UserFactory()
    client.force_login(u)
    resp = client.post("/topup/new/", {
        "amount": "5000.00",
        "date": date.today().isoformat(),
        "comment": "Получил от Серика",
    })
    assert resp.status_code == 302
    assert Topup.objects.filter(user=u, source="employee").count() == 1
    assert get_balance(u) == Decimal("5000.00")


@pytest.mark.django_db
def test_topup_create_rejects_empty_comment(client):
    u = UserFactory()
    client.force_login(u)
    resp = client.post("/topup/new/", {
        "amount": "5000.00",
        "date": date.today().isoformat(),
        "comment": "",
    })
    assert resp.status_code == 200  # stays on form
    assert Topup.objects.count() == 0
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Append to `expenses/views.py`**

```python
from expenses.forms import EmployeeTopupForm
from expenses.services.topups import create_topup


@login_required
def topup_create(request):
    form = EmployeeTopupForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        topup = create_topup(
            created_by=request.user,
            user=request.user,
            amount=form.cleaned_data["amount"],
            topup_date=form.cleaned_data["date"],
            comment=form.cleaned_data["comment"],
            source="employee",
        )
        for f in request.FILES.getlist("attachments"):
            from expenses.models import ExpenseAttachment
            # Reuse attachment model — store on a dummy expense? No.
            # For now, skip file attachment on topups. Phase 3 can add TopupAttachment.
            pass
        messages.success(request, "Приход добавлен")
        return redirect("cabinet")
    return render(request, "expenses/topup_form.html", {"form": form})
```

- [ ] **Step 4: Add route to `expenses/urls.py`**

Add before the `attachments/` line:

```python
    path("topup/new/", views.topup_create, name="topup_create"),
```

- [ ] **Step 5: Create placeholder `templates/expenses/topup_form.html`**

```html
{% extends "base.html" %}
{% block title %}Приход{% endblock %}
{% block content %}
<h1>Добавить приход</h1>
<form method="post">
  {% csrf_token %}
  {% if form.non_field_errors %}<div class="errors">{{ form.non_field_errors }}</div>{% endif %}
  {% for field in form %}
    <label>{{ field.label }}</label>
    {{ field }}
    {{ field.errors }}
  {% endfor %}
  <button type="submit">Сохранить</button>
  <a href="{% url 'cabinet' %}">Отмена</a>
</form>
{% endblock %}
```

(This will be redesigned in Task 9.)

- [ ] **Step 6: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_topup.py -v
```

Expected: 3 PASS.

- [ ] **Step 7: Commit**

```bash
git add expenses/views.py expenses/urls.py templates/expenses/topup_form.html tests/test_views_topup.py
git commit -m "feat(expenses): add employee topup view"
```

---

### Task 5: Update admin — source column and filter

**Files:**
- Modify: `expenses/admin.py`
- Modify: `tests/test_admin.py`

- [ ] **Step 1: Append test to `tests/test_admin.py`**

```python
@pytest.mark.django_db
def test_admin_topups_shows_source(client):
    admin = AdminFactory()
    u = UserFactory()
    TopupFactory(user=u, created_by=admin)
    client.force_login(admin)
    resp = client.get("/admin/expenses/topup/")
    assert resp.status_code == 200
```

- [ ] **Step 2: Update `TopupAdmin` in `expenses/admin.py`**

Change:

```python
@admin.register(Topup)
class TopupAdmin(admin.ModelAdmin):
    list_display = ("date", "user", "amount", "source", "comment", "created_by", "created_at")
    list_filter = ("user", "date", "source")
    search_fields = ("comment",)
    date_hierarchy = "date"

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        if not change and not obj.source:
            obj.source = "admin"
        super().save_model(request, obj, form, change)
```

- [ ] **Step 3: Run**

```bash
POSTGRES_HOST=localhost pytest tests/test_admin.py -v
```

- [ ] **Step 4: Commit**

```bash
git add expenses/admin.py tests/test_admin.py
git commit -m "feat(expenses): add source column and filter to Topup admin"
```

---

# Part B: Web Redesign (Tasks 6–12)

---

### Task 6: Design system CSS + base.html redesign

**Files:**
- Create: `static/css/style.css`
- Rewrite: `templates/base.html`
- Rewrite: `templates/accounts/login.html`

- [ ] **Step 1: Create `static/css/style.css`**

```css
:root {
  --color-primary: #009C96;
  --color-primary-dark: #007A75;
  --color-danger: #E5002D;
  --color-danger-light: #FFF0F3;
  --color-bg: #FAFAFA;
  --color-surface: #FFFFFF;
  --color-text: #231815;
  --color-text-secondary: #6B7280;
  --color-border: #E5E7EB;
  --color-success: #009C96;
  --color-success-bg: #F0FAFA;
  --radius: 12px;
  --radius-sm: 8px;
  --shadow: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font);
  background: var(--color-bg);
  color: var(--color-text);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app {
  max-width: 480px;
  margin: 0 auto;
  width: 100%;
  flex: 1;
  padding: 1rem;
  padding-bottom: 5rem;
}

/* Balance card */
.balance-card {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.5rem;
  text-align: center;
  margin-bottom: 1rem;
}
.balance-card__label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.25rem;
}
.balance-card__amount {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--color-primary);
}
.balance-card__amount.negative {
  color: var(--color-danger);
}

/* Action buttons row */
.actions {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.875rem 1.5rem;
  border-radius: var(--radius-sm);
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
  min-height: 48px;
}
.btn:active { opacity: 0.8; }
.btn--primary {
  flex: 2;
  background: var(--color-primary);
  color: white;
}
.btn--outline {
  flex: 1;
  background: transparent;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
}
.btn--danger {
  background: var(--color-danger);
  color: white;
}
.btn--full {
  width: 100%;
}
.btn--sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  min-height: 36px;
}

/* Operations list */
.ops-list {
  list-style: none;
}
.ops-list__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 0.75rem;
}
.op-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--color-border);
  text-decoration: none;
  color: inherit;
}
.op-item:last-child { border-bottom: none; }
.op-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}
.op-icon.expense { background: var(--color-danger-light); color: var(--color-danger); }
.op-icon.topup { background: var(--color-success-bg); color: var(--color-success); }
.op-details { flex: 1; min-width: 0; }
.op-details__category {
  font-size: 0.9375rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.op-details__date {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
.op-amount {
  font-weight: 600;
  font-size: 0.9375rem;
  white-space: nowrap;
}
.op-amount.expense { color: var(--color-danger); }
.op-amount.topup { color: var(--color-primary); }

/* Tab bar */
.tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: center;
  padding: 0.5rem 0;
  z-index: 100;
}
.tab-bar__inner {
  display: flex;
  max-width: 480px;
  width: 100%;
}
.tab-bar__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.125rem;
  padding: 0.375rem;
  text-decoration: none;
  color: var(--color-text-secondary);
  font-size: 0.6875rem;
  font-weight: 500;
}
.tab-bar__item.active { color: var(--color-primary); }
.tab-bar__icon { font-size: 1.25rem; }

/* Forms */
.form-card {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.5rem;
}
.form-group {
  margin-bottom: 1rem;
}
.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 0.375rem;
}
.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 1rem;
  font-family: var(--font);
  background: var(--color-bg);
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(0,156,150,0.15);
}
.form-error {
  color: var(--color-danger);
  font-size: 0.8125rem;
  margin-top: 0.25rem;
}
.form-errors {
  background: var(--color-danger-light);
  color: var(--color-danger);
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

/* Misc */
.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 1rem;
}
.link-more {
  display: block;
  text-align: center;
  color: var(--color-primary);
  font-weight: 500;
  padding: 0.75rem;
  text-decoration: none;
}
.messages {
  list-style: none;
  margin-bottom: 1rem;
}
.messages li {
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
}
.messages .success {
  background: var(--color-success-bg);
  color: var(--color-primary-dark);
}

/* Desktop: hide tab bar, show top nav */
@media (min-width: 481px) {
  .app { max-width: 600px; padding-bottom: 2rem; }
  .tab-bar { display: none; }
  .desktop-nav { display: flex !important; }
}
.desktop-nav {
  display: none;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
  padding: 0.75rem 1rem;
  gap: 1.5rem;
  align-items: center;
}
.desktop-nav a {
  color: var(--color-text-secondary);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
}
.desktop-nav a.active { color: var(--color-primary); }
.desktop-nav .spacer { flex: 1; }
```

- [ ] **Step 2: Rewrite `templates/base.html`**

```html
{% load static %}
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}ManyTracker{% endblock %}</title>
<link rel="stylesheet" href="{% static 'css/style.css' %}">
</head>
<body>
{% if user.is_authenticated %}
<nav class="desktop-nav">
  <a href="{% url 'cabinet' %}" {% if active_tab == 'cabinet' %}class="active"{% endif %}>Кабинет</a>
  <a href="{% url 'history' %}" {% if active_tab == 'history' %}class="active"{% endif %}>История</a>
  <a href="{% url 'profile' %}" {% if active_tab == 'profile' %}class="active"{% endif %}>Профиль</a>
  <span class="spacer"></span>
  <a href="{% url 'logout' %}">Выйти</a>
</nav>
{% endif %}

<main class="app">
  {% if messages %}
  <ul class="messages">
    {% for m in messages %}<li class="{{ m.tags }}">{{ m }}</li>{% endfor %}
  </ul>
  {% endif %}
  {% block content %}{% endblock %}
</main>

{% if user.is_authenticated %}
<nav class="tab-bar">
  <div class="tab-bar__inner">
    <a href="{% url 'cabinet' %}" class="tab-bar__item {% if active_tab == 'cabinet' %}active{% endif %}">
      <span class="tab-bar__icon">&#8962;</span>Кабинет
    </a>
    <a href="{% url 'history' %}" class="tab-bar__item {% if active_tab == 'history' %}active{% endif %}">
      <span class="tab-bar__icon">&#9776;</span>История
    </a>
    <a href="{% url 'profile' %}" class="tab-bar__item {% if active_tab == 'profile' %}active{% endif %}">
      <span class="tab-bar__icon">&#9786;</span>Профиль
    </a>
  </div>
</nav>
{% endif %}
</body>
</html>
```

- [ ] **Step 3: Rewrite `templates/accounts/login.html`**

```html
{% extends "base.html" %}
{% block title %}Вход — ManyTracker{% endblock %}
{% block content %}
<div style="display:flex;flex-direction:column;align-items:center;padding-top:3rem">
  <h1 class="page-title">ManyTracker</h1>
  <div class="form-card" style="width:100%;max-width:360px">
    <form method="post">
      {% csrf_token %}
      {% if form.non_field_errors %}
        <div class="form-errors">{{ form.non_field_errors }}</div>
      {% endif %}
      {% for field in form %}
        <div class="form-group">
          <label>{{ field.label }}</label>
          {{ field }}
        </div>
      {% endfor %}
      <button type="submit" class="btn btn--primary btn--full">Войти</button>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Delete `static/.keep` if it exists, CSS file replaces it**

```bash
rm -f static/.keep
```

- [ ] **Step 5: Verify**

```bash
POSTGRES_HOST=localhost python manage.py check
POSTGRES_HOST=localhost pytest -v
```

Expected: all tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add static/css/style.css templates/base.html templates/accounts/login.html
git commit -m "feat(ui): add Wedrink-inspired design system and redesigned base/login"
```

---

### Task 7: Redesign cabinet.html

**Files:**
- Rewrite: `templates/expenses/cabinet.html`
- Modify: `expenses/views.py` — cabinet view returns unified operations list

- [ ] **Step 1: Update `cabinet` view in `expenses/views.py`**

Replace the `cabinet` function:

```python
from itertools import chain
from operator import attrgetter


@login_required
def cabinet(request):
    balance = get_balance(request.user)
    expenses = list(
        Expense.objects.filter(user=request.user, is_deleted=False)
        .select_related("category")[:10]
    )
    topups = list(Topup.objects.filter(user=request.user)[:10])

    operations = sorted(
        chain(
            [{"type": "expense", "date": e.date, "label": e.category_display(),
              "amount": e.amount, "id": e.id, "created_at": e.created_at} for e in expenses],
            [{"type": "topup", "date": t.date, "label": t.comment or "Пополнение",
              "amount": t.amount, "id": t.id, "created_at": t.created_at} for t in topups],
        ),
        key=lambda x: (x["date"], x["created_at"]),
        reverse=True,
    )[:10]

    return render(request, "expenses/cabinet.html", {
        "balance": balance,
        "operations": operations,
        "active_tab": "cabinet",
    })
```

- [ ] **Step 2: Rewrite `templates/expenses/cabinet.html`**

```html
{% extends "base.html" %}
{% block title %}Кабинет — ManyTracker{% endblock %}
{% block content %}
<div class="balance-card">
  <div class="balance-card__label">Баланс</div>
  <div class="balance-card__amount {% if balance < 0 %}negative{% endif %}">
    {{ balance }} ₸
  </div>
</div>

<div class="actions">
  <a href="{% url 'expense_create' %}" class="btn btn--primary">Расход</a>
  <a href="{% url 'topup_create' %}" class="btn btn--outline">Приход</a>
</div>

<div class="ops-list__title">Последние операции</div>
<ul class="ops-list">
  {% for op in operations %}
  <li>
    <a href="{% if op.type == 'expense' %}{% url 'expense_detail' op.id %}{% else %}#{% endif %}" class="op-item">
      <div class="op-icon {{ op.type }}">{% if op.type == 'expense' %}↓{% else %}↑{% endif %}</div>
      <div class="op-details">
        <div class="op-details__category">{{ op.label }}</div>
        <div class="op-details__date">{{ op.date|date:"d.m.Y" }}</div>
      </div>
      <div class="op-amount {{ op.type }}">
        {% if op.type == 'expense' %}−{% else %}+{% endif %}{{ op.amount }} ₸
      </div>
    </a>
  </li>
  {% empty %}
  <li style="padding:1rem;text-align:center;color:var(--color-text-secondary)">Пока ничего нет</li>
  {% endfor %}
</ul>

{% if operations %}
<a href="{% url 'history' %}" class="link-more">Вся история →</a>
{% endif %}
{% endblock %}
```

- [ ] **Step 3: Run tests**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_cabinet.py -v
```

Expected: PASS (view still returns 200 with balance).

- [ ] **Step 4: Commit**

```bash
git add expenses/views.py templates/expenses/cabinet.html
git commit -m "feat(ui): redesign cabinet with wallet-style layout"
```

---

### Task 8: Redesign expense_form, expense_detail, confirm_delete

**Files:**
- Rewrite: `templates/expenses/expense_form.html`, `templates/expenses/expense_detail.html`, `templates/expenses/confirm_delete.html`

- [ ] **Step 1: Rewrite `templates/expenses/expense_form.html`**

```html
{% extends "base.html" %}
{% block title %}{% if edit_mode %}Редактировать{% else %}Новый расход{% endif %}{% endblock %}
{% block content %}
<h1 class="page-title">{% if edit_mode %}Редактировать расход{% else %}Новый расход{% endif %}</h1>
{% if warning %}
  <div class="form-errors">{{ warning }}</div>
{% endif %}
<div class="form-card">
  <form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    {% if form.non_field_errors %}<div class="form-errors">{{ form.non_field_errors }}</div>{% endif %}
    <div class="form-group">
      <label>{{ form.category.label }}</label>
      {{ form.category }}
      {% if form.category.errors %}<div class="form-error">{{ form.category.errors }}</div>{% endif %}
    </div>
    <div class="form-group">
      <label>{{ form.custom_category_name.label }}</label>
      {{ form.custom_category_name }}
    </div>
    <div class="form-group">
      <label>{{ form.amount.label }}</label>
      {{ form.amount }}
      {% if form.amount.errors %}<div class="form-error">{{ form.amount.errors }}</div>{% endif %}
    </div>
    <div class="form-group">
      <label>{{ form.date.label }}</label>
      {{ form.date }}
      {% if form.date.errors %}<div class="form-error">{{ form.date.errors }}</div>{% endif %}
    </div>
    <div class="form-group">
      <label>{{ form.comment.label }}</label>
      {{ form.comment }}
    </div>
    {% if not edit_mode %}
    <div class="form-group">
      <label>Файлы (до 10 МБ)</label>
      <input type="file" name="attachments" multiple>
    </div>
    {% endif %}
    {% if warning %}<input type="hidden" name="confirm_negative" value="on">{% endif %}
    <button type="submit" class="btn btn--primary btn--full">
      {% if warning %}Подтвердить{% else %}Сохранить{% endif %}
    </button>
    <a href="{% url 'cabinet' %}" class="btn btn--outline btn--full" style="margin-top:0.5rem">Отмена</a>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 2: Rewrite `templates/expenses/expense_detail.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1 class="page-title">Трата #{{ expense.id }}</h1>
<div class="form-card">
  <div class="form-group"><label>Дата</label><div>{{ expense.date|date:"d.m.Y" }}</div></div>
  <div class="form-group"><label>Категория</label><div>{{ expense.category_display }}</div></div>
  <div class="form-group"><label>Сумма</label><div style="font-weight:700;color:var(--color-danger)">−{{ expense.amount }} ₸</div></div>
  <div class="form-group"><label>Комментарий</label><div>{{ expense.comment|default:"—" }}</div></div>
  <div class="form-group">
    <label>Файлы</label>
    <ul style="list-style:none;padding:0">
      {% for a in expense.attachments.all %}
        <li><a href="{% url 'attachment_download' a.id %}" style="color:var(--color-primary)">{{ a.original_name }}</a></li>
      {% empty %}
        <li style="color:var(--color-text-secondary)">нет</li>
      {% endfor %}
    </ul>
  </div>
</div>
<div style="margin-top:1rem;display:flex;gap:0.5rem">
  <a href="{% url 'expense_edit' expense.id %}" class="btn btn--outline" style="flex:1">Редактировать</a>
  <a href="{% url 'expense_delete' expense.id %}" class="btn btn--danger btn--sm" style="flex:1">Удалить</a>
</div>
<a href="{% url 'cabinet' %}" class="link-more">← назад</a>
{% endblock %}
```

- [ ] **Step 3: Rewrite `templates/expenses/confirm_delete.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1 class="page-title">Удалить трату?</h1>
<div class="form-card" style="text-align:center">
  <p>{{ expense.date|date:"d.m.Y" }} — {{ expense.category_display }} — {{ expense.amount }} ₸</p>
  <form method="post" style="margin-top:1rem">
    {% csrf_token %}
    <button type="submit" class="btn btn--danger btn--full">Да, удалить</button>
    <a href="{% url 'expense_detail' expense.id %}" class="btn btn--outline btn--full" style="margin-top:0.5rem">Отмена</a>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 4: Run all tests**

```bash
POSTGRES_HOST=localhost pytest -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/expenses/expense_form.html templates/expenses/expense_detail.html templates/expenses/confirm_delete.html
git commit -m "feat(ui): redesign expense form, detail, and delete pages"
```

---

### Task 9: Redesign topup_form.html

**Files:**
- Rewrite: `templates/expenses/topup_form.html`

- [ ] **Step 1: Rewrite `templates/expenses/topup_form.html`**

```html
{% extends "base.html" %}
{% block title %}Приход{% endblock %}
{% block content %}
<h1 class="page-title">Добавить приход</h1>
<div class="form-card">
  <form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    {% if form.non_field_errors %}<div class="form-errors">{{ form.non_field_errors }}</div>{% endif %}
    <div class="form-group">
      <label>{{ form.amount.label }}</label>
      {{ form.amount }}
      {% if form.amount.errors %}<div class="form-error">{{ form.amount.errors }}</div>{% endif %}
    </div>
    <div class="form-group">
      <label>{{ form.date.label }}</label>
      {{ form.date }}
      {% if form.date.errors %}<div class="form-error">{{ form.date.errors }}</div>{% endif %}
    </div>
    <div class="form-group">
      <label>{{ form.comment.label }}</label>
      {{ form.comment }}
      {% if form.comment.errors %}<div class="form-error">{{ form.comment.errors }}</div>{% endif %}
    </div>
    <button type="submit" class="btn btn--primary btn--full">Сохранить</button>
    <a href="{% url 'cabinet' %}" class="btn btn--outline btn--full" style="margin-top:0.5rem">Отмена</a>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 2: Run tests → PASS**

- [ ] **Step 3: Commit**

```bash
git add templates/expenses/topup_form.html
git commit -m "feat(ui): redesign topup form"
```

---

### Task 10: Redesign history.html (unified timeline)

**Files:**
- Modify: `expenses/views.py` — history returns unified ops
- Rewrite: `templates/expenses/history.html`

- [ ] **Step 1: Update `history` view in `expenses/views.py`**

Replace the `history` function:

```python
@login_required
def history(request):
    expenses_qs = Expense.objects.filter(user=request.user, is_deleted=False).select_related("category")
    topups_qs = Topup.objects.filter(user=request.user)
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    if date_from:
        try:
            d = datetime.strptime(date_from, "%Y-%m-%d").date()
            expenses_qs = expenses_qs.filter(date__gte=d)
            topups_qs = topups_qs.filter(date__gte=d)
        except ValueError:
            pass
    if date_to:
        try:
            d = datetime.strptime(date_to, "%Y-%m-%d").date()
            expenses_qs = expenses_qs.filter(date__lte=d)
            topups_qs = topups_qs.filter(date__lte=d)
        except ValueError:
            pass

    operations = sorted(
        chain(
            [{"type": "expense", "date": e.date, "label": e.category_display(),
              "amount": e.amount, "id": e.id, "comment": e.comment,
              "created_at": e.created_at} for e in expenses_qs],
            [{"type": "topup", "date": t.date, "label": t.comment or "Пополнение",
              "amount": t.amount, "id": t.id, "comment": t.comment,
              "created_at": t.created_at} for t in topups_qs],
        ),
        key=lambda x: (x["date"], x["created_at"]),
        reverse=True,
    )

    return render(request, "expenses/history.html", {
        "operations": operations,
        "date_from": date_from, "date_to": date_to,
        "active_tab": "history",
    })
```

Add `from itertools import chain` at the top if not already present (added in Task 7).

- [ ] **Step 2: Rewrite `templates/expenses/history.html`**

```html
{% extends "base.html" %}
{% block title %}История{% endblock %}
{% block content %}
<h1 class="page-title">История</h1>
<div class="form-card" style="margin-bottom:1rem">
  <form method="get" style="display:flex;gap:0.5rem;align-items:end">
    <div class="form-group" style="flex:1;margin:0">
      <label>С</label>
      <input type="date" name="from" value="{{ date_from|default:'' }}">
    </div>
    <div class="form-group" style="flex:1;margin:0">
      <label>По</label>
      <input type="date" name="to" value="{{ date_to|default:'' }}">
    </div>
    <button type="submit" class="btn btn--primary btn--sm">ОК</button>
  </form>
</div>

<ul class="ops-list">
  {% for op in operations %}
  <li>
    <a href="{% if op.type == 'expense' %}{% url 'expense_detail' op.id %}{% else %}#{% endif %}" class="op-item">
      <div class="op-icon {{ op.type }}">{% if op.type == 'expense' %}↓{% else %}↑{% endif %}</div>
      <div class="op-details">
        <div class="op-details__category">{{ op.label }}</div>
        <div class="op-details__date">{{ op.date|date:"d.m.Y" }}</div>
      </div>
      <div class="op-amount {{ op.type }}">
        {% if op.type == 'expense' %}−{% else %}+{% endif %}{{ op.amount }} ₸
      </div>
    </a>
  </li>
  {% empty %}
  <li style="padding:2rem;text-align:center;color:var(--color-text-secondary)">Нет операций за этот период</li>
  {% endfor %}
</ul>
{% endblock %}
```

- [ ] **Step 3: Run tests**

```bash
POSTGRES_HOST=localhost pytest tests/test_views_history.py -v
```

Expected: PASS (history still returns 200, content assertions use amount values that are still present).

- [ ] **Step 4: Commit**

```bash
git add expenses/views.py templates/expenses/history.html
git commit -m "feat(ui): redesign history with unified timeline"
```

---

### Task 11: Profile page with Telegram linking

**Files:**
- Modify: `expenses/views.py`, `expenses/urls.py`
- Create: `templates/expenses/profile.html`

- [ ] **Step 1: Add profile view to `expenses/views.py`**

```python
import random
import string
from django.utils import timezone
from datetime import timedelta


@login_required
def profile(request):
    link_code = None
    if request.method == "POST" and "generate_code" in request.POST:
        code = "".join(random.choices(string.digits, k=6))
        request.user.telegram_link_code = code
        request.user.telegram_link_code_expires_at = timezone.now() + timedelta(minutes=10)
        request.user.save(update_fields=["telegram_link_code", "telegram_link_code_expires_at"])
        link_code = code
    elif request.method == "POST" and "unlink_telegram" in request.POST:
        request.user.telegram_id = None
        request.user.telegram_link_code = None
        request.user.save(update_fields=["telegram_id", "telegram_link_code"])
        messages.success(request, "Telegram отвязан")
    return render(request, "expenses/profile.html", {
        "active_tab": "profile",
        "link_code": link_code,
    })
```

- [ ] **Step 2: Add route to `expenses/urls.py`**

```python
    path("profile/", views.profile, name="profile"),
```

- [ ] **Step 3: Create `templates/expenses/profile.html`**

```html
{% extends "base.html" %}
{% block title %}Профиль{% endblock %}
{% block content %}
<h1 class="page-title">Профиль</h1>
<div class="form-card">
  <div class="form-group"><label>Имя</label><div>{{ user.full_name|default:user.username }}</div></div>
  <div class="form-group"><label>Логин</label><div>{{ user.username }}</div></div>
</div>

<h2 class="page-title" style="margin-top:1.5rem">Telegram</h2>
<div class="form-card">
  {% if user.telegram_id %}
    <p>Привязан (ID: {{ user.telegram_id }})</p>
    <form method="post" style="margin-top:0.75rem">
      {% csrf_token %}
      <button name="unlink_telegram" class="btn btn--outline btn--full btn--sm">Отвязать</button>
    </form>
  {% elif link_code %}
    <p style="margin-bottom:0.5rem">Ваш код привязки:</p>
    <div style="font-size:2rem;font-weight:700;letter-spacing:0.3rem;text-align:center;padding:1rem;background:var(--color-bg);border-radius:var(--radius-sm)">{{ link_code }}</div>
    <p style="margin-top:0.75rem;font-size:0.875rem;color:var(--color-text-secondary)">
      Отправьте боту <code>/start {{ link_code }}</code>. Код действует 10 минут.
    </p>
  {% else %}
    <p style="color:var(--color-text-secondary)">Telegram не привязан</p>
    <form method="post" style="margin-top:0.75rem">
      {% csrf_token %}
      <button name="generate_code" class="btn btn--primary btn--full">Привязать Telegram</button>
    </form>
  {% endif %}
</div>

<a href="{% url 'logout' %}" class="btn btn--outline btn--full" style="margin-top:1.5rem">Выйти</a>
{% endblock %}
```

- [ ] **Step 4: Run tests**

```bash
POSTGRES_HOST=localhost pytest -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add expenses/views.py expenses/urls.py templates/expenses/profile.html
git commit -m "feat(ui): add profile page with Telegram linking"
```

---

### Task 12: Add `active_tab` to all remaining views + visual smoke test

**Files:**
- Modify: `expenses/views.py` — add `active_tab` to all render calls

- [ ] **Step 1: Add `active_tab` to all views**

In `expense_create`, `expense_edit`, `expense_detail`, `expense_delete`, `topup_create` — add `"active_tab": "cabinet"` to the context dict passed to `render()`.

In `history` view — already has `"active_tab": "history"` (added in Task 10).

In `profile` view — already has `"active_tab": "profile"` (added in Task 11).

- [ ] **Step 2: Run all tests**

```bash
POSTGRES_HOST=localhost pytest -v
```

Expected: all PASS.

- [ ] **Step 3: Manual browser smoke test**

```bash
POSTGRES_HOST=localhost python manage.py runserver
```

Open http://localhost:8000/login/ — verify new design. Login → cabinet should show wallet-style layout with teal/red palette, bottom tab bar on mobile viewport (use Chrome DevTools device mode). Check: Расход button, Приход button, operations list with colors.

- [ ] **Step 4: Commit**

```bash
git add expenses/views.py
git commit -m "feat(ui): add active_tab context to all views"
```

---

# Part C: Telegram Bot (Tasks 13–20)

---

### Task 13: Bot app scaffolding + management command

**Files:**
- Create: `bot/` app structure, `bot/management/commands/run_bot.py`
- Modify: `config/settings.py`

- [ ] **Step 1: Create bot app**

```bash
cd /Users/adletkartov/Documents/my-project
python manage.py startapp bot
mkdir -p bot/management/commands bot/handlers
touch bot/management/__init__.py bot/management/commands/__init__.py bot/handlers/__init__.py
```

- [ ] **Step 2: Write `bot/apps.py`**

```python
from django.apps import AppConfig


class BotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bot"
```

- [ ] **Step 3: Add `"bot"` to `INSTALLED_APPS` in `config/settings.py`**

After `"expenses",`, add `"bot",`.

Also add to settings:

```python
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
```

- [ ] **Step 4: Write `bot/management/commands/run_bot.py`**

```python
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram.ext import ApplicationBuilder

from bot.handlers.start import get_start_handler
from bot.handlers.menu import get_menu_handler
from bot.handlers.balance import get_balance_handler
from bot.handlers.add_expense import get_expense_handler
from bot.handlers.add_topup import get_topup_handler
from bot.handlers.history import get_history_handler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Telegram bot"

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stderr.write("TELEGRAM_BOT_TOKEN is not set")
            return

        app = ApplicationBuilder().token(token).build()

        app.add_handler(get_start_handler())
        app.add_handler(get_expense_handler())
        app.add_handler(get_topup_handler())
        app.add_handler(get_balance_handler())
        app.add_handler(get_history_handler())
        app.add_handler(get_menu_handler())

        self.stdout.write("Bot starting...")
        app.run_polling(drop_pending_updates=True)
```

- [ ] **Step 5: Create empty handler files** (implemented in subsequent tasks)

```bash
for f in start menu balance add_expense add_topup history; do
  cat > bot/handlers/$f.py << 'PYEOF'
def get_${f}_handler():
    raise NotImplementedError
PYEOF
done
```

Actually, create proper stubs:

`bot/handlers/start.py`:
```python
def get_start_handler():
    raise NotImplementedError
```

`bot/handlers/menu.py`:
```python
def get_menu_handler():
    raise NotImplementedError
```

`bot/handlers/balance.py`:
```python
def get_balance_handler():
    raise NotImplementedError
```

`bot/handlers/add_expense.py`:
```python
def get_expense_handler():
    raise NotImplementedError
```

`bot/handlers/add_topup.py`:
```python
def get_topup_handler():
    raise NotImplementedError
```

`bot/handlers/history.py`:
```python
def get_history_handler():
    raise NotImplementedError
```

- [ ] **Step 6: Write `bot/keyboards.py`** (stub, implemented in Task 16)

```python
# Keyboards defined in Task 16
```

- [ ] **Step 7: Commit**

```bash
git add bot/ config/settings.py
git commit -m "feat(bot): scaffold bot app with management command"
```

---

### Task 14: Docker Compose bot service + env

**Files:**
- Modify: `docker-compose.yml`, `.env.example`

- [ ] **Step 1: Add `bot` service to `docker-compose.yml`**

After the `web` service, add:

```yaml
  bot:
    build: .
    restart: unless-stopped
    env_file: .env
    command: python manage.py run_bot
    depends_on:
      - postgres
```

- [ ] **Step 2: Add `TELEGRAM_BOT_TOKEN` to `.env.example`**

Append:

```
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "feat(bot): add bot service to Docker Compose"
```

---

### Task 15: /start + link code handler

**Files:**
- Rewrite: `bot/handlers/start.py`
- Create: `tests/test_bot_start.py`

- [ ] **Step 1: Write test `tests/test_bot_start.py`**

```python
from datetime import timedelta
import pytest
from django.utils import timezone
from unittest.mock import AsyncMock, MagicMock
from tests.factories import UserFactory

from bot.handlers.start import link_user_by_code


@pytest.mark.django_db
def test_link_user_by_valid_code():
    u = UserFactory()
    u.telegram_link_code = "123456"
    u.telegram_link_code_expires_at = timezone.now() + timedelta(minutes=5)
    u.save()

    result = link_user_by_code("123456", telegram_id=99999)
    assert result is not None
    assert result.username == u.username
    u.refresh_from_db()
    assert u.telegram_id == 99999
    assert u.telegram_link_code is None


@pytest.mark.django_db
def test_link_user_expired_code():
    u = UserFactory()
    u.telegram_link_code = "654321"
    u.telegram_link_code_expires_at = timezone.now() - timedelta(minutes=1)
    u.save()

    result = link_user_by_code("654321", telegram_id=88888)
    assert result is None


@pytest.mark.django_db
def test_link_user_invalid_code():
    result = link_user_by_code("000000", telegram_id=77777)
    assert result is None
```

- [ ] **Step 2: Run → FAIL**

```bash
source .venv/bin/activate
POSTGRES_HOST=localhost pytest tests/test_bot_start.py -v
```

- [ ] **Step 3: Rewrite `bot/handlers/start.py`**

```python
from django.contrib.auth import get_user_model
from django.utils import timezone
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

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
        return  # already linked, let other handlers process

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
```

- [ ] **Step 4: Update `bot/keyboards.py`** (minimal, enough for start handler)

```python
from telegram import ReplyKeyboardMarkup


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["Баланс"],
            ["Расход", "Приход"],
            ["История"],
        ],
        resize_keyboard=True,
    )
```

- [ ] **Step 5: Run → PASS**

```bash
POSTGRES_HOST=localhost pytest tests/test_bot_start.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add bot/handlers/start.py bot/keyboards.py tests/test_bot_start.py
git commit -m "feat(bot): add /start command with link code authentication"
```

---

### Task 16: Menu handler

**Files:**
- Rewrite: `bot/handlers/menu.py`

- [ ] **Step 1: Write `bot/handlers/menu.py`**

```python
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.handlers.start import get_user_by_telegram_id
from bot.keyboards import main_menu_keyboard


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт. Отправьте /start")
        return
    await update.message.reply_text(
        "Используйте меню ниже",
        reply_markup=main_menu_keyboard(),
    )


def get_menu_handler():
    return MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command)
```

Note: This is the fallback handler — it's added last in `run_bot.py` so it only catches messages not handled by other handlers.

- [ ] **Step 2: Commit**

```bash
git add bot/handlers/menu.py
git commit -m "feat(bot): add fallback menu handler"
```

---

### Task 17: Balance handler

**Files:**
- Rewrite: `bot/handlers/balance.py`
- Create: `tests/test_bot_balance.py`

- [ ] **Step 1: Write test `tests/test_bot_balance.py`**

```python
from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory
from expenses.services.balance import get_balance


@pytest.mark.django_db
def test_balance_for_linked_user():
    u = UserFactory()
    u.telegram_id = 12345
    u.save()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("50000"), created_by=admin)
    assert get_balance(u) == Decimal("50000.00")
```

- [ ] **Step 2: Write `bot/handlers/balance.py`**

```python
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.handlers.start import get_user_by_telegram_id
from expenses.services.balance import get_balance


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт: /start")
        return
    balance = get_balance(user)
    sign = "+" if balance >= 0 else ""
    await update.message.reply_text(f"Ваш баланс: {sign}{balance} ₸")


def get_balance_handler():
    return MessageHandler(filters.Regex("^Баланс$"), balance_handler)
```

- [ ] **Step 3: Run**

```bash
POSTGRES_HOST=localhost pytest tests/test_bot_balance.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add bot/handlers/balance.py tests/test_bot_balance.py
git commit -m "feat(bot): add balance handler"
```

---

### Task 18: Expense FSM handler

**Files:**
- Rewrite: `bot/handlers/add_expense.py`
- Create: `tests/test_bot_expense.py`

- [ ] **Step 1: Write test `tests/test_bot_expense.py`**

```python
from datetime import date
from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory, CategoryFactory
from expenses.services.expenses import create_expense
from expenses.models import Expense


@pytest.mark.django_db
def test_create_expense_via_service_for_bot():
    u = UserFactory()
    u.telegram_id = 12345
    u.save()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory(name="Такси")
    e = create_expense(
        user=u, category=cat, custom_name="",
        amount=Decimal("1500"), expense_date=date.today(),
        comment="", created_via="telegram",
    )
    assert e.created_via == "telegram"
    assert Expense.objects.filter(user=u, created_via="telegram").count() == 1
```

- [ ] **Step 2: Write `bot/handlers/add_expense.py`**

```python
from datetime import date
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.handlers.start import get_user_by_telegram_id
from bot.keyboards import main_menu_keyboard
from expenses.models import ExpenseCategory
from expenses.services.balance import get_balance
from expenses.services.expenses import NegativeBalanceError, create_expense

CATEGORY, CUSTOM_NAME, AMOUNT, COMMENT, FILE, CONFIRM = range(6)


def _category_keyboard():
    cats = list(ExpenseCategory.objects.filter(is_active=True).order_by("sort_order", "name"))
    buttons = [[InlineKeyboardButton(c.name, callback_data=f"cat_{c.id}")] for c in cats]
    buttons.append([InlineKeyboardButton("Другое", callback_data="cat_other")])
    return InlineKeyboardMarkup(buttons)


async def expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт: /start")
        return ConversationHandler.END
    context.user_data["expense_user"] = user
    await update.message.reply_text("Выберите категорию:", reply_markup=_category_keyboard())
    return CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "cat_other":
        context.user_data["expense_category"] = None
        await query.edit_message_text("Введите название категории:")
        return CUSTOM_NAME
    cat_id = int(data.replace("cat_", ""))
    try:
        cat = ExpenseCategory.objects.get(id=cat_id)
    except ExpenseCategory.DoesNotExist:
        await query.edit_message_text("Категория не найдена. Попробуйте снова.")
        return ConversationHandler.END
    context.user_data["expense_category"] = cat
    context.user_data["expense_custom_name"] = ""
    await query.edit_message_text(f"Категория: {cat.name}\nВведите сумму (₸):")
    return AMOUNT


async def custom_name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Введите название:")
        return CUSTOM_NAME
    context.user_data["expense_custom_name"] = name
    await update.message.reply_text(f"Категория: {name}\nВведите сумму (₸):")
    return AMOUNT


async def amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".").replace(" ", "")
    try:
        amount = Decimal(text)
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await update.message.reply_text("Введите корректную сумму больше нуля:")
        return AMOUNT
    context.user_data["expense_amount"] = amount
    await update.message.reply_text("Комментарий (или нажмите /skip):")
    return COMMENT


async def comment_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_comment"] = update.message.text.strip()
    await update.message.reply_text("Отправьте фото или документ чека (или /skip):")
    return FILE


async def comment_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_comment"] = ""
    await update.message.reply_text("Отправьте фото или документ чека (или /skip):")
    return FILE


async def file_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_file"] = update.message.document or update.message.photo
    return await _show_confirm(update, context)


async def file_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_file"] = None
    return await _show_confirm(update, context)


async def _show_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    cat = ud.get("expense_category")
    cat_name = cat.name if cat else ud.get("expense_custom_name", "")
    amount = ud["expense_amount"]
    user = ud["expense_user"]
    balance = get_balance(user)
    projected = balance - amount

    text = f"Расход: {cat_name}\nСумма: {amount} ₸"
    if projected < 0:
        text += f"\n⚠️ Баланс станет {projected} ₸"
    text += "\n\nПодтвердить?"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Подтвердить", callback_data="confirm_yes"),
         InlineKeyboardButton("Отмена", callback_data="confirm_no")],
    ])
    await update.message.reply_text(text, reply_markup=kb)
    return CONFIRM


async def confirm_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    user = ud["expense_user"]
    try:
        expense = create_expense(
            user=user,
            category=ud.get("expense_category"),
            custom_name=ud.get("expense_custom_name", ""),
            amount=ud["expense_amount"],
            expense_date=date.today(),
            comment=ud.get("expense_comment", ""),
            created_via="telegram",
            allow_negative=True,
        )
    except Exception as e:
        await query.edit_message_text(f"Ошибка: {e}")
        return ConversationHandler.END

    balance = get_balance(user)
    await query.edit_message_text(
        f"✓ Расход: −{expense.amount} ₸ ({expense.category_display()})\nБаланс: {balance} ₸",
    )
    return ConversationHandler.END


async def confirm_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Отменено.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def get_expense_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Расход$"), expense_start)],
        states={
            CATEGORY: [CallbackQueryHandler(category_chosen)],
            CUSTOM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_name_entered)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_entered)],
            COMMENT: [
                CommandHandler("skip", comment_skip),
                MessageHandler(filters.TEXT & ~filters.COMMAND, comment_entered),
            ],
            FILE: [
                CommandHandler("skip", file_skip),
                MessageHandler(filters.Document.ALL | filters.PHOTO, file_received),
            ],
            CONFIRM: [CallbackQueryHandler(confirm_yes, pattern="^confirm_yes$"),
                       CallbackQueryHandler(confirm_no, pattern="^confirm_no$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
```

- [ ] **Step 3: Run**

```bash
POSTGRES_HOST=localhost pytest tests/test_bot_expense.py -v
```

- [ ] **Step 4: Commit**

```bash
git add bot/handlers/add_expense.py tests/test_bot_expense.py
git commit -m "feat(bot): add expense FSM conversation handler"
```

---

### Task 19: Topup FSM handler (employee)

**Files:**
- Rewrite: `bot/handlers/add_topup.py`
- Create: `tests/test_bot_topup.py`

- [ ] **Step 1: Write test `tests/test_bot_topup.py`**

```python
from datetime import date
from decimal import Decimal
import pytest
from tests.factories import UserFactory
from expenses.services.topups import create_topup
from expenses.models import Topup


@pytest.mark.django_db
def test_create_topup_via_service_for_bot():
    u = UserFactory()
    u.telegram_id = 12345
    u.save()
    topup = create_topup(
        created_by=u, user=u, amount=Decimal("5000"),
        topup_date=date.today(), comment="Получил от Серика",
        source="employee",
    )
    assert topup.source == "employee"
    assert Topup.objects.filter(user=u, source="employee").count() == 1
```

- [ ] **Step 2: Write `bot/handlers/add_topup.py`**

```python
from datetime import date
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.handlers.start import get_user_by_telegram_id
from bot.keyboards import main_menu_keyboard
from expenses.services.balance import get_balance
from expenses.services.topups import create_topup

AMOUNT, COMMENT, CONFIRM = range(3)


async def topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт: /start")
        return ConversationHandler.END
    context.user_data["topup_user"] = user
    await update.message.reply_text("Введите сумму прихода (₸):")
    return AMOUNT


async def amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".").replace(" ", "")
    try:
        amount = Decimal(text)
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await update.message.reply_text("Введите корректную сумму больше нуля:")
        return AMOUNT
    context.user_data["topup_amount"] = amount
    await update.message.reply_text("Комментарий (от кого / за что):")
    return COMMENT


async def comment_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text.strip()
    if not comment:
        await update.message.reply_text("Комментарий обязателен. Напишите от кого / за что:")
        return COMMENT
    context.user_data["topup_comment"] = comment

    amount = context.user_data["topup_amount"]
    text = f"Приход: +{amount} ₸\nКомментарий: {comment}\n\nПодтвердить?"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Подтвердить", callback_data="topup_yes"),
         InlineKeyboardButton("Отмена", callback_data="topup_no")],
    ])
    await update.message.reply_text(text, reply_markup=kb)
    return CONFIRM


async def confirm_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    user = ud["topup_user"]
    try:
        topup = create_topup(
            created_by=user, user=user,
            amount=ud["topup_amount"],
            topup_date=date.today(),
            comment=ud["topup_comment"],
            source="employee",
        )
    except Exception as e:
        await query.edit_message_text(f"Ошибка: {e}")
        return ConversationHandler.END

    balance = get_balance(user)
    await query.edit_message_text(
        f"✓ Приход: +{topup.amount} ₸\nБаланс: {balance} ₸",
    )
    return ConversationHandler.END


async def confirm_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Отменено.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def get_topup_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Приход$"), topup_start)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_entered)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment_entered)],
            CONFIRM: [CallbackQueryHandler(confirm_yes, pattern="^topup_yes$"),
                       CallbackQueryHandler(confirm_no, pattern="^topup_no$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
```

- [ ] **Step 3: Run**

```bash
POSTGRES_HOST=localhost pytest tests/test_bot_topup.py -v
```

- [ ] **Step 4: Commit**

```bash
git add bot/handlers/add_topup.py tests/test_bot_topup.py
git commit -m "feat(bot): add topup FSM conversation handler"
```

---

### Task 20: History handler

**Files:**
- Rewrite: `bot/handlers/history.py`
- Create: `tests/test_bot_history.py`

- [ ] **Step 1: Write test `tests/test_bot_history.py`**

```python
from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory, ExpenseFactory, CategoryFactory


@pytest.mark.django_db
def test_history_data_exists_for_user():
    u = UserFactory()
    u.telegram_id = 12345
    u.save()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("50000"), created_by=admin)
    cat = CategoryFactory(name="Обед")
    ExpenseFactory(user=u, amount=Decimal("3000"), category=cat)
    from expenses.models import Expense, Topup
    assert Expense.objects.filter(user=u).count() == 1
    assert Topup.objects.filter(user=u).count() == 1
```

- [ ] **Step 2: Write `bot/handlers/history.py`**

```python
from itertools import chain

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.handlers.start import get_user_by_telegram_id
from expenses.models import Expense, Topup


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт: /start")
        return

    expenses = Expense.objects.filter(
        user=user, is_deleted=False
    ).select_related("category").order_by("-date", "-created_at")[:10]

    topups = Topup.objects.filter(user=user).order_by("-date", "-created_at")[:10]

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
```

- [ ] **Step 3: Run**

```bash
POSTGRES_HOST=localhost pytest tests/test_bot_history.py -v
```

- [ ] **Step 4: Run full suite**

```bash
POSTGRES_HOST=localhost pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/history.py tests/test_bot_history.py
git commit -m "feat(bot): add history handler"
```

---

### Task 21: Update run_bot to use text_code_handler + final integration

**Files:**
- Modify: `bot/management/commands/run_bot.py`

- [ ] **Step 1: Update `run_bot.py`** to register text_code_handler for linking

```python
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from bot.handlers.start import get_start_handler, text_code_handler
from bot.handlers.menu import get_menu_handler
from bot.handlers.balance import get_balance_handler
from bot.handlers.add_expense import get_expense_handler
from bot.handlers.add_topup import get_topup_handler
from bot.handlers.history import get_history_handler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Telegram bot"

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stderr.write("TELEGRAM_BOT_TOKEN is not set")
            return

        app = ApplicationBuilder().token(token).build()

        app.add_handler(get_start_handler())
        app.add_handler(get_expense_handler())
        app.add_handler(get_topup_handler())
        app.add_handler(get_balance_handler())
        app.add_handler(get_history_handler())
        # text_code_handler for 6-digit codes from unlinked users
        app.add_handler(MessageHandler(
            filters.Regex(r"^\d{6}$") & ~filters.COMMAND,
            text_code_handler,
        ))
        # Fallback — must be last
        app.add_handler(get_menu_handler())

        self.stdout.write("Bot starting...")
        app.run_polling(drop_pending_updates=True)
```

- [ ] **Step 2: Run full test suite**

```bash
POSTGRES_HOST=localhost pytest -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add bot/management/commands/run_bot.py
git commit -m "feat(bot): wire all handlers in run_bot command"
```

---

## Done Criteria

- [ ] All pytest tests pass
- [ ] `Topup.source` field works; employee can create self-topup via web
- [ ] Admin sees source column in topups, can filter
- [ ] Web cabinet shows wallet-style design: balance card, Расход/Приход buttons, unified colored history
- [ ] Mobile-first layout with bottom tab bar (< 480px), desktop nav (> 480px)
- [ ] Profile page with Telegram link code generation
- [ ] Telegram bot: /start with code linking, Баланс, Расход (FSM), Приход (FSM), История
- [ ] Login page redesigned
- [ ] All forms touch-friendly with Wedrink palette
- [ ] `docker compose up` runs web + bot + postgres

---

## Self-Review

**Spec coverage:**
- Topup source field + migration → Task 1 ✓
- create_topup with source + employee validation → Task 2 ✓
- EmployeeTopupForm → Task 3 ✓
- Employee topup view → Task 4 ✓
- Admin source column/filter → Task 5 ✓
- Design system CSS → Task 6 ✓
- Cabinet redesign (wallet-style) → Task 7 ✓
- Expense form/detail/delete redesign → Task 8 ✓
- Topup form redesign → Task 9 ✓
- History unified timeline → Task 10 ✓
- Profile with Telegram linking → Task 11 ✓
- Active tab in all views + responsive → Task 12 ✓
- Bot scaffolding → Task 13 ✓
- Docker Compose bot service → Task 14 ✓
- /start + link code → Task 15 ✓
- Menu handler → Task 16 ✓
- Balance handler → Task 17 ✓
- Expense FSM → Task 18 ✓
- Topup FSM (employee) → Task 19 ✓
- History handler → Task 20 ✓
- run_bot integration → Task 21 ✓

**Out of scope:** admin notifications about employee topups (Phase 3), dashboard (Phase 3), production deploy (Phase 4).
