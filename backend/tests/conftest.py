import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from tests.helpers import PASSWORD


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    # Login throttling counts attempts in the cache; start every test fresh.
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    """An API client that enforces CSRF exactly like a browser session would."""
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="alice", password=PASSWORD)
