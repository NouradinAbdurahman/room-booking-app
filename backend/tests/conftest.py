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


@pytest.fixture
def room(db):
    from rooms.models import Room

    return Room.objects.create(name="Conference Room A", capacity=10)


@pytest.fixture
def other_room(db):
    from rooms.models import Room

    return Room.objects.create(name="Focus Room", capacity=4)


@pytest.fixture
def logged_in(api_client, user):
    """A client already logged in as `user` (CSRF is covered by the auth tests)."""
    api_client.force_authenticate(user)
    return api_client


@pytest.fixture
def make_booking(room, user):
    """Write a Booking straight to the database (the room and user fixtures by default)."""
    from bookings.models import Booking

    def _make(start, end, *, booker=None, booking_room=None, title="Sync", **extra):
        return Booking.objects.create(
            room=booking_room or room, user=booker or user, title=title, start_time=start, end_time=end, **extra
        )

    return _make


@pytest.fixture
def server_clock(monkeypatch):
    """Pin the clock the booking rules trust; returns a setter for 'now'."""

    def set_now(now):
        monkeypatch.setattr("bookings.services.current_time", lambda: now)

    return set_now
