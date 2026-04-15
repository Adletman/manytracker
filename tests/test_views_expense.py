from decimal import Decimal
from datetime import date
import pytest
from tests.factories import UserFactory, AdminFactory, TopupFactory, CategoryFactory
from expenses.models import Expense


@pytest.mark.django_db
def test_create_expense_happy_path(client):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u)
    resp = client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1500.00", "date": date.today().isoformat(), "comment": "обед",
    })
    assert resp.status_code == 302
    assert Expense.objects.filter(user=u).count() == 1


@pytest.mark.django_db
def test_create_expense_shows_negative_warning(client):
    u = UserFactory()
    cat = CategoryFactory()
    client.force_login(u)
    resp = client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000.00", "date": date.today().isoformat(), "comment": "",
    })
    assert resp.status_code == 200
    assert "Баланс станет".encode("utf-8") in resp.content
    assert Expense.objects.count() == 0


@pytest.mark.django_db
def test_create_expense_confirm_negative(client):
    u = UserFactory()
    cat = CategoryFactory()
    client.force_login(u)
    resp = client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000.00", "date": date.today().isoformat(), "comment": "",
        "confirm_negative": "on",
    })
    assert resp.status_code == 302
    assert Expense.objects.count() == 1


from datetime import timedelta
from django.utils import timezone


@pytest.mark.django_db
def test_owner_can_edit_within_24h(client):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u)
    client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000", "date": date.today().isoformat(), "comment": "",
    })
    expense = Expense.objects.get(user=u)
    resp = client.post(f"/expenses/{expense.id}/edit/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1200", "date": date.today().isoformat(), "comment": "fix",
    })
    assert resp.status_code == 302
    expense.refresh_from_db()
    assert expense.amount == Decimal("1200")


@pytest.mark.django_db
def test_owner_cannot_edit_others(client):
    u1 = UserFactory()
    u2 = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u1, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u1)
    client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000", "date": date.today().isoformat(), "comment": "",
    })
    expense = Expense.objects.get(user=u1)
    client.force_login(u2)
    resp = client.get(f"/expenses/{expense.id}/edit/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_owner_cannot_edit_after_24h(client):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u)
    client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000", "date": date.today().isoformat(), "comment": "",
    })
    expense = Expense.objects.get(user=u)
    Expense.objects.filter(pk=expense.pk).update(
        created_at=timezone.now() - timedelta(hours=25)
    )
    resp = client.post(f"/expenses/{expense.id}/edit/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1200", "date": date.today().isoformat(),
    })
    assert resp.status_code == 403


@pytest.mark.django_db
def test_delete_soft_deletes(client):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    client.force_login(u)
    client.post("/expenses/new/", {
        "category": cat.id, "custom_category_name": "",
        "amount": "1000", "date": date.today().isoformat(), "comment": "",
    })
    expense = Expense.objects.get(user=u)
    resp = client.post(f"/expenses/{expense.id}/delete/")
    assert resp.status_code == 302
    expense.refresh_from_db()
    assert expense.is_deleted
