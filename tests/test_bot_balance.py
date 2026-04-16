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
