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
