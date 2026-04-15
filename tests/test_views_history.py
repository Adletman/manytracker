from datetime import date
from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory, ExpenseFactory, CategoryFactory


@pytest.mark.django_db
def test_history_shows_own_expenses_only(client):
    u1 = UserFactory()
    u2 = UserFactory()
    cat = CategoryFactory(name="Такси")
    ExpenseFactory(user=u1, amount=Decimal("1000"), category=cat)
    ExpenseFactory(user=u2, amount=Decimal("9999"), category=cat)
    client.force_login(u1)
    resp = client.get("/history/")
    assert resp.status_code == 200
    assert b"1000" in resp.content
    assert b"9999" not in resp.content


@pytest.mark.django_db
def test_history_filters_by_date_range(client):
    u = UserFactory()
    cat = CategoryFactory()
    ExpenseFactory(user=u, amount=Decimal("1111"), date=date(2026, 1, 1), category=cat)
    ExpenseFactory(user=u, amount=Decimal("2222"), date=date(2026, 4, 1), category=cat)
    client.force_login(u)
    resp = client.get("/history/?from=2026-03-01&to=2026-04-30")
    assert b"2222" in resp.content
    assert b"1111" not in resp.content
