"""Only PostgreSQL's 23P01 from no_overlapping_active_bookings becomes 409 (ADR 0001).
Every error here is a real one raised by PostgreSQL, not a fake."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError, connection

from bookings import services
from bookings.models import Booking
from rooms.models import Room

pytestmark = pytest.mark.django_db

DOHA = ZoneInfo("Asia/Qatar")


@pytest.fixture(autouse=True)
def fixed_clock(server_clock):
    server_clock(datetime(2026, 10, 20, 8, tzinfo=DOHA))




def book(client, room, start="10:00", end="11:00"):
    return client.post(
        "/api/bookings/",
        {
            "room_id": room.id,
            "title": "Sync",
            "start_time": f"2026-10-20T{start}:00+03:00",
            "end_time": f"2026-10-20T{end}:00+03:00",
        },
        format="json",
    )


def test_exclusion_violation_from_the_database_itself_is_a_409(logged_in, room, monkeypatch):
    """The race: the pre-check saw no Conflict, but PostgreSQL refuses the insert."""
    assert book(logged_in, room).status_code == 201
    real_check = services._overlapping_booking
    calls = []

    def first_check_misses(*args):
        calls.append(args)
        return None if len(calls) == 1 else real_check(*args)

    monkeypatch.setattr(services, "_overlapping_booking", first_check_misses)

    response = book(logged_in, room, "10:30", "11:30")

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "booking_conflict",
        "message": "Conference Room A is already booked 10:00–11:00.",
        "fields": {},
    }
    assert Booking.objects.count() == 1


def test_23P01_from_another_constraint_is_not_a_booking_conflict(logged_in, room, user):
    """Same SQLSTATE, different constraint: must not be reported as a Room conflict."""
    other_room = Room.objects.create(name="Focus Room", capacity=4)
    with connection.cursor() as cursor:  # rolled back with the test's transaction
        cursor.execute(
            "ALTER TABLE bookings_booking ADD CONSTRAINT one_room_per_user_at_a_time "
            "EXCLUDE USING gist (user_id WITH =, tstzrange(start_time, end_time, '[)') WITH &&)"
        )
    assert book(logged_in, room).status_code == 201

    with pytest.raises(IntegrityError) as excinfo:
        book(logged_in, other_room)

    assert excinfo.value.__cause__.sqlstate == "23P01"
    assert excinfo.value.__cause__.diag.constraint_name == "one_room_per_user_at_a_time"


def test_unrelated_integrity_error_propagates_and_is_not_a_409(logged_in, room, user, monkeypatch):
    """A different database error (here a CHECK violation) is never turned into a conflict."""

    def insert_that_breaks_a_check(**fields):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO bookings_booking (title, start_time, end_time, status, created_at, updated_at, room_id, user_id) "
                "VALUES ('   ', %s, %s, 'active', now(), now(), %s, %s)",
                [fields["start_time"], fields["end_time"], fields["room"].id, fields["user"].id],
            )

    monkeypatch.setattr(Booking.objects, "create", insert_that_breaks_a_check)

    with pytest.raises(IntegrityError) as excinfo:
        book(logged_in, room)

    assert excinfo.value.__cause__.diag.constraint_name == "booking_title_not_blank"


def test_conflict_whose_booking_is_gone_on_re_read_says_at_that_time(logged_in, room, monkeypatch):
    """The other Booking was cancelled between the refusal and the re-read."""
    assert book(logged_in, room).status_code == 201
    monkeypatch.setattr(services, "_overlapping_booking", lambda *args: None)

    response = book(logged_in, room, "10:30", "11:30")

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Conference Room A is already booked at that time."

