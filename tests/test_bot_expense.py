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
