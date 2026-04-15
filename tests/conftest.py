import pytest


@pytest.fixture
def user_data():
    return {
        "username": "alice",
        "password": "secretpass123",
        "full_name": "Alice Worker",
    }
