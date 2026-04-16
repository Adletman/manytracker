from datetime import timedelta
import pytest
from django.utils import timezone
from tests.factories import UserFactory

from bot.handlers.start import link_user_by_code_sync as link_user_by_code


@pytest.mark.django_db
def test_link_user_by_valid_code():
    u = UserFactory()
    u.telegram_link_code = "123456"
    u.telegram_link_code_expires_at = timezone.now() + timedelta(minutes=5)
    u.save()

    result = link_user_by_code("123456", telegram_id=99999)
    assert result is not None
    assert result.username == u.username
    u.refresh_from_db()
    assert u.telegram_id == 99999
    assert u.telegram_link_code is None


@pytest.mark.django_db
def test_link_user_expired_code():
    u = UserFactory()
    u.telegram_link_code = "654321"
    u.telegram_link_code_expires_at = timezone.now() - timedelta(minutes=1)
    u.save()

    result = link_user_by_code("654321", telegram_id=88888)
    assert result is None


@pytest.mark.django_db
def test_link_user_invalid_code():
    result = link_user_by_code("000000", telegram_id=77777)
    assert result is None
