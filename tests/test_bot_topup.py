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
