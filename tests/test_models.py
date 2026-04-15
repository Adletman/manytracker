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


from expenses.models import ExpenseCategory


@pytest.mark.django_db
def test_expense_category_ordering():
    c1 = ExpenseCategory.objects.create(name="Обед", sort_order=2)
    c2 = ExpenseCategory.objects.create(name="Такси", sort_order=1)
    names = list(ExpenseCategory.objects.values_list("name", flat=True))
    assert names == ["Такси", "Обед"]


from datetime import date
from decimal import Decimal
from expenses.models import Topup


@pytest.mark.django_db
def test_topup_creation():
    user = User.objects.create_user(username="topupuser", password="x" * 10)
    admin = User.objects.create_superuser(username="topupadmin", password="x" * 10)
    t = Topup.objects.create(
        user=user, amount=Decimal("50000.00"), date=date(2026, 4, 1),
        comment="Аванс", created_by=admin,
    )
    assert t.amount == Decimal("50000.00")
    assert t.user == user
