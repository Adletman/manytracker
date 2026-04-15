from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory


@pytest.mark.django_db
def test_cabinet_requires_login(client):
    resp = client.get("/cabinet/")
    assert resp.status_code == 302
    assert "/login/" in resp["Location"]


@pytest.mark.django_db
def test_cabinet_shows_balance(client):
    u = UserFactory(username="alice")
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("50000.00"), created_by=admin)
    client.force_login(u)
    resp = client.get("/cabinet/")
    assert resp.status_code == 200
    assert b"50000" in resp.content
