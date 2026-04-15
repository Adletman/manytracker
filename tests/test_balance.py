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
