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
        created_by=admin, user=u, amount=Decimal("50000.00"),
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
        create_topup(created_by=admin, user=u, amount=Decimal("0"), topup_date=date.today())
