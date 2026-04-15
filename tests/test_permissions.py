import pytest
from tests.factories import UserFactory, AdminFactory


@pytest.mark.django_db
def test_non_admin_cannot_access_admin_site(client):
    u = UserFactory()
    client.force_login(u)
    resp = client.get("/admin/")
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_admin_can_access_admin_site(client):
    admin = AdminFactory()
    client.force_login(admin)
    resp = client.get("/admin/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_anonymous_redirected_from_cabinet(client):
    resp = client.get("/cabinet/")
    assert resp.status_code == 302
    assert "/login/" in resp["Location"]


@pytest.mark.django_db
def test_anonymous_redirected_from_history(client):
    resp = client.get("/history/")
    assert resp.status_code == 302
