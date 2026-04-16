from decimal import Decimal
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory


@pytest.mark.django_db
def test_admin_users_list_shows_balance(client):
    admin = AdminFactory()
    u = UserFactory(username="alice")
    TopupFactory(user=u, amount=Decimal("12345.00"), created_by=admin)
    client.force_login(admin)
    resp = client.get("/admin/accounts/user/")
    assert resp.status_code == 200
    assert b"12345" in resp.content


@pytest.mark.django_db
def test_admin_expenses_list(client):
    admin = AdminFactory()
    u = UserFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    from tests.factories import ExpenseFactory, CategoryFactory
    cat = CategoryFactory(name="Такси")
    ExpenseFactory(user=u, amount=Decimal("2500"), category=cat)
    client.force_login(admin)
    resp = client.get("/admin/expenses/expense/")
    assert resp.status_code == 200
    assert b"2500" in resp.content


@pytest.mark.django_db
def test_admin_topups_shows_source(client):
    admin = AdminFactory()
    u = UserFactory()
    TopupFactory(user=u, created_by=admin)
    client.force_login(admin)
    resp = client.get("/admin/expenses/topup/")
    assert resp.status_code == 200
