import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_create_user_hashes_password():
    user = User.objects.create_user(username="alice", password="secretpass123", full_name="Alice")
    assert user.username == "alice"
    assert user.check_password("secretpass123")
    assert not user.is_admin
    assert user.is_active


@pytest.mark.django_db
def test_create_superuser_flags():
    admin = User.objects.create_superuser(username="boss", password="adminpass123")
    assert admin.is_admin
    assert admin.is_staff
    assert admin.is_superuser
