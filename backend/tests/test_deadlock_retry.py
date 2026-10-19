"""A deadlock on insert is retried, never reported (ADR 0001).

Two truly simultaneous overlapping inserts can deadlock inside PostgreSQL's
exclusion check (SQLSTATE 40P01). A real deadlock cannot be produced on demand,
so these tests raise it the way Django delivers it: an OperationalError caused
by psycopg's own DeadlockDetected class. The live proof that real deadlocks
happen and are handled is tests/test_concurrent_booking.py.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.db import OperationalError
from psycopg.errors import DeadlockDetected

from bookings import services
from bookings.models import Booking

pytestmark = pytest.mark.django_db

DOHA = ZoneInfo("Asia/Qatar")


@pytest.fixture(autouse=True)
def fixed_clock(server_clock):
    server_clock(datetime(2026, 10, 20, 8, tzinfo=DOHA))


def deadlock():
    return OperationalError("deadlock detected")


def book(client, room):
    return client.post(
        "/api/bookings/",
        {
            "room_id": room.id,
            "title": "Sync",
            "start_time": "2026-10-20T10:00:00+03:00",
            "end_time": "2026-10-20T11:00:00+03:00",
        },
        format="json",
    )


def test_a_deadlock_on_insert_is_retried(logged_in, room, monkeypatch):
    real_create = Booking.objects.create
    attempts = []

    def deadlock_once(**fields):
        attempts.append(fields)
        if len(attempts) == 1:
            raise deadlock() from DeadlockDetected("deadlock detected")
        return real_create(**fields)

    monkeypatch.setattr(Booking.objects, "create", deadlock_once)

    response = book(logged_in, room)

    assert response.status_code == 201
    assert len(attempts) == 2


def test_a_deadlock_that_keeps_happening_is_raised_after_every_attempt(logged_in, room, monkeypatch):
    """Retrying stops after INSERT_ATTEMPTS; the error is then raised, not hidden or called a Conflict."""
    attempts = []

    def always_deadlock(**fields):
        attempts.append(fields)
        raise deadlock() from DeadlockDetected("deadlock detected")

    monkeypatch.setattr(Booking.objects, "create", always_deadlock)

    with pytest.raises(OperationalError):
        book(logged_in, room)

    assert len(attempts) == services.INSERT_ATTEMPTS
