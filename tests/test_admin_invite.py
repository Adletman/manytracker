from unittest.mock import patch
import pytest
from django.utils import timezone
from tests.factories import UserFactory, AdminFactory


def _url(user_id):
    return f"/admin/accounts/user/{user_id}/gen-tg-code/"


@pytest.mark.django_db
def test_generate_code_requires_staff(client):
    u = UserFactory()
    resp = client.post(_url(u.id))
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_generate_code_success(client, settings):
    settings.TELEGRAM_BOT_USERNAME = "TestBot"
    admin = AdminFactory()
    u = UserFactory()
    client.force_login(admin)

    resp = client.post(_url(u.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"].isdigit() and len(data["code"]) == 6
    assert "TestBot" in data["copy_text"]
    assert data["code"] in data["copy_text"]

    u.refresh_from_db()
    assert u.telegram_link_code == data["code"]
    assert u.telegram_link_code_expires_at > timezone.now()


@pytest.mark.django_db
def test_generate_code_collision_retry(client):
    admin = AdminFactory()
    existing = UserFactory(telegram_link_code="111111")
    target = UserFactory()
    client.force_login(admin)

    with patch("accounts.admin_views.secrets.randbelow", side_effect=[111111, 222222]):
        resp = client.post(_url(target.id))

    assert resp.status_code == 200
    assert resp.json()["code"] == "222222"
    target.refresh_from_db()
    assert target.telegram_link_code == "222222"


@pytest.mark.django_db
def test_generate_code_get_not_allowed(client):
    admin = AdminFactory()
    u = UserFactory()
    client.force_login(admin)
    resp = client.get(_url(u.id))
    assert resp.status_code == 405
