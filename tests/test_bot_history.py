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
