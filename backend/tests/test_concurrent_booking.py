"""Brief rule 6 / ADR 0001: two people booking the same Slot at the same moment.

Each request runs in its own thread, with its own logged-in client and its own
PostgreSQL connection (Django opens one connection per thread). The test is
transactional, so rows committed by one connection are visible to the other,
as in production. Nothing about the database is mocked.
"""

import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient

from bookings import services
from bookings.models import Booking, BookingStatus
from rooms.models import Room
from tests.helpers import PASSWORD, csrf_token, login

pytestmark = pytest.mark.django_db(transaction=True)

DOHA = ZoneInfo("Asia/Qatar")
FIRST_DAY = datetime(2026, 10, 21, tzinfo=DOHA)
TIMEOUT = 10  # seconds; a barrier that never fills fails the test instead of hanging


@pytest.fixture(autouse=True)
def fixed_clock(server_clock):
    server_clock(datetime(2026, 10, 20, 7, tzinfo=DOHA))


@pytest.fixture
def room(transactional_db):
    return Room.objects.create(name="Conference Room A", capacity=10)


@pytest.fixture
def alice_and_bob(transactional_db):
    """Two different Users, each logged in through the real CSRF-checked flow."""
    clients = []
    for username in ("alice", "bob"):
        get_user_model().objects.create_user(username=username, password=PASSWORD)
        client = APIClient(enforce_csrf_checks=True)
        assert login(client, csrf_token(client), username=username).status_code == 200
        clients.append(client)
    return clients


def release_together(room, requests):
    """Send each (client, start, end) booking request from its own thread, all
    released at the same instant by a barrier; return the responses in order."""
    start_line = threading.Barrier(len(requests), timeout=TIMEOUT)
    responses = [None] * len(requests)

    def send(index, client, start, end):
        try:
            start_line.wait()
            responses[index] = client.post(
                "/api/bookings/",
                {
                    "room_id": room.id,
                    "title": f"Meeting {index}",
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                },
                format="json",
                HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            )
        finally:
            connection.close()  # this thread's own PostgreSQL connection

    threads = [threading.Thread(target=send, args=(i, *request)) for i, request in enumerate(requests)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(TIMEOUT)
    assert not any(thread.is_alive() for thread in threads), "a request never finished"
    return responses


def active_bookings_on(room, day):
    return Booking.objects.filter(
        room=room,
        status=BookingStatus.ACTIVE,
        start_time__gte=day,
        start_time__lt=day + timedelta(days=1),
    ).count()


def test_forced_race_only_postgresql_stops_the_second_booking(room, alice_and_bob, monkeypatch):
    """Both requests finish the friendly pre-check, each seeing a free Slot,
    before either inserts. The application cannot see the Conflict, so only
    the exclusion constraint can refuse the second Booking."""
    real_pre_check = services._overlapping_booking
    both_checked = threading.Barrier(2, timeout=TIMEOUT)
    first_pass_results = []

    def pre_check_then_wait_for_the_other_request(*args):
        result = real_pre_check(*args)
        if len(first_pass_results) < 2:  # the two pre-checks, not the later re-read
            first_pass_results.append(result)
            both_checked.wait()
        return result

    monkeypatch.setattr(services, "_overlapping_booking", pre_check_then_wait_for_the_other_request)
    start, end = FIRST_DAY.replace(hour=10), FIRST_DAY.replace(hour=11)
    alice, bob = alice_and_bob

    responses = release_together(room, [(alice, start, end), (bob, start, end)])

    assert first_pass_results == [None, None], "both requests saw a free Slot"
    assert sorted(r.status_code for r in responses) == [201, 409]
    refused = next(r for r in responses if r.status_code == 409)
    assert refused.json()["error"] == {
        "code": "booking_conflict",
        "message": "Conference Room A is already booked 10:00–11:00.",
        "fields": {},
    }
    assert active_bookings_on(room, FIRST_DAY) == 1


@pytest.mark.parametrize(
    "second_slot",
    [(10, 0, 11, 0), (10, 30, 11, 30)],
    ids=["identical-slots", "partly-overlapping-slots"],
)
def test_natural_race_repeated_always_leaves_exactly_one_booking(room, alice_and_bob, second_slot):
    """No hooks: release both requests at once, 20 times, each round on a fresh Day."""
    alice, bob = alice_and_bob
    start_hour, start_minute, end_hour, end_minute = second_slot

    for round_number in range(20):
        day = FIRST_DAY + timedelta(days=round_number)
        responses = release_together(
            room,
            [
                (alice, day.replace(hour=10), day.replace(hour=11)),
                (
                    bob,
                    day.replace(hour=start_hour, minute=start_minute),
                    day.replace(hour=end_hour, minute=end_minute),
                ),
            ],
        )

        assert sorted(r.status_code for r in responses) == [201, 409], f"round {round_number}"
        assert active_bookings_on(room, day) == 1, f"round {round_number}"
