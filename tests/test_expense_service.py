from datetime import date, timedelta
from decimal import Decimal
import pytest
from django.utils import timezone
from tests.factories import UserFactory, AdminFactory, CategoryFactory, TopupFactory
from expenses.services.expenses import (
    create_expense,
    update_expense,
    delete_expense,
    NegativeBalanceError,
    EditWindowExpiredError,
)
from expenses.models import Expense, AuditLog


@pytest.mark.django_db
def test_create_expense_happy_path():
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000.00"), created_by=admin)
    cat = CategoryFactory(name="Такси-svc")
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
