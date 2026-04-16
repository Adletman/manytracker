from decimal import Decimal
from datetime import date
import pytest
from tests.factories import UserFactory
from expenses.models import Topup
from expenses.services.balance import get_balance


@pytest.mark.django_db
def test_topup_create_requires_login(client):
    resp = client.get("/topup/new/")
    assert resp.status_code == 302
    assert "/login/" in resp["Location"]


@pytest.mark.django_db
def test_topup_create_happy_path(client):
    u = UserFactory()
    client.force_login(u)
    resp = client.post("/topup/new/", {
        "amount": "5000.00",
        "date": date.today().isoformat(),
        "comment": "Получил от Серика",
    })
    assert resp.status_code == 302
    assert Topup.objects.filter(user=u, source="employee").count() == 1
    assert get_balance(u) == Decimal("5000.00")


@pytest.mark.django_db
def test_topup_create_rejects_empty_comment(client):
    u = UserFactory()
    client.force_login(u)
    resp = client.post("/topup/new/", {
        "amount": "5000.00",
        "date": date.today().isoformat(),
        "comment": "",
    })
    assert resp.status_code == 200
    assert Topup.objects.count() == 0
