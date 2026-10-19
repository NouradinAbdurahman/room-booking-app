"""Brief rule 6 / ADR 0001: two people booking the same Slot at the same moment.

Each request runs in its own thread, with its own logged-in client and its own
PostgreSQL connection (Django opens one connection per thread). The test is
transactional, so rows committed by one connection are visible to the other,
as in production. Nothing about the database is mocked.
"""

import threading
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient

from bookings import services
from bookings.models import Booking, BookingStatus
from tests.helpers import PASSWORD, csrf_token, login

pytestmark = pytest.mark.django_db(transaction=True)

DOHA = ZoneInfo("Asia/Qatar")
FIRST_DAY = datetime(2026, 10, 21, tzinfo=DOHA)
TIMEOUT = 10  # seconds; a barrier that never fills fails the test instead of hanging
CONFLICT = {"status": 409, "code": "booking_conflict"}


@pytest.fixture(autouse=True)
def fixed_clock(server_clock):
    server_clock(datetime(2026, 10, 20, 7, tzinfo=DOHA))


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
    released at the same instant by a barrier; return the responses in order.
    An exception inside any thread is re-raised here, not swallowed."""
    start_line = threading.Barrier(len(requests), timeout=TIMEOUT)
    responses = [None] * len(requests)
    failures = [None] * len(requests)

    def send(index, client, start, end):
        try:
            start_line.wait()
            responses[index] = client.post(
                "/api/bookings/",
                {
                    "room_id": room.id,
                    "title": f"Sync {index}",
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                },
                format="json",
                HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            )
        except BaseException as error:  # noqa: BLE001 - re-raised in the test thread below
            failures[index] = error
        finally:
            connection.close()  # this thread's own PostgreSQL connection

    threads = [threading.Thread(target=send, args=(i, *request)) for i, request in enumerate(requests)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(TIMEOUT)
    assert not any(thread.is_alive() for thread in threads), "a request never finished"
    for failure in failures:
        if failure is not None:
            raise failure
    return responses


def outcome(response):
    body = response.json() if response.status_code >= 400 else {}
    return {"status": response.status_code, "code": body.get("error", {}).get("code")}


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
    record = threading.Lock()

    def pre_check_then_wait_for_the_other_request(*args):
        result = real_pre_check(*args)
        with record:
            is_first_pass = len(first_pass_results) < 2  # not the later re-read
            if is_first_pass:
                first_pass_results.append(result)
        if is_first_pass:
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
    "bobs_slot",
    [(time(10, 0), time(11, 0)), (time(10, 30), time(11, 30))],
    ids=["identical-slots", "partly-overlapping-slots"],
)
def test_natural_race_repeated_always_leaves_exactly_one_booking(room, alice_and_bob, bobs_slot):
    """No hooks: Alice books 10:00-11:00 while Bob books bobs_slot at the same
    instant, 20 times, each round on a fresh Day."""
    alice, bob = alice_and_bob

    for round_number in range(20):
        day = FIRST_DAY + timedelta(days=round_number)
        at = lambda t: day.replace(hour=t.hour, minute=t.minute)  # noqa: E731
        responses = release_together(
            room,
            [(alice, at(time(10, 0)), at(time(11, 0))), (bob, at(bobs_slot[0]), at(bobs_slot[1]))],
        )

        outcomes = sorted((outcome(r) for r in responses), key=lambda o: o["status"])
        assert outcomes == [{"status": 201, "code": None}, CONFLICT], f"round {round_number}"
        assert active_bookings_on(room, day) == 1, f"round {round_number}"
