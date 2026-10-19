"""Seam 1: GET /api/bookings/?mine=true, the session User's Upcoming bookings (ADR 0006)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from bookings.models import BookingStatus

pytestmark = pytest.mark.django_db

DOHA = ZoneInfo("Asia/Qatar")
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=DOHA)
HOUR = timedelta(hours=1)


@pytest.fixture(autouse=True)
def fixed_clock(server_clock):
    server_clock(NOW)


@pytest.fixture
def bob(db):
    return get_user_model().objects.create_user(username="bob")


def my_bookings(client, **params):
    return client.get("/api/bookings/", {"mine": "true", **params})


def titles(response):
    return [b["title"] for b in response.json()["results"]]


def test_logged_out_user_gets_401(api_client):
    response = my_bookings(api_client)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_only_my_upcoming_active_bookings_are_listed(logged_in, make_booking, bob, other_room):
    make_booking(NOW + HOUR, NOW + 2 * HOUR, title="Mine, later today")
    make_booking(NOW + HOUR * 30, NOW + HOUR * 31, title="Mine, other room", booking_room=other_room)
    make_booking(NOW - HOUR / 2, NOW + HOUR / 2, title="Mine, in progress")
    make_booking(NOW - 2 * HOUR, NOW - HOUR, title="Mine, ended")
    make_booking(NOW - HOUR, NOW, title="Mine, ended exactly now", booking_room=other_room)
    make_booking(NOW + 3 * HOUR, NOW + 4 * HOUR, title="Mine, cancelled", status=BookingStatus.CANCELLED, cancelled_at=NOW)
    make_booking(NOW + 5 * HOUR, NOW + 6 * HOUR, title="Bob's", booker=bob)

    response = my_bookings(logged_in)

    assert response.status_code == 200
    assert titles(response) == ["Mine, in progress", "Mine, later today", "Mine, other room"]
    assert {b["booked_by"]["username"] for b in response.json()["results"]} == {"alice"}


def test_bookings_are_in_the_agreed_shape_in_doha_time(logged_in, make_booking, room, user):
    booking = make_booking(NOW + HOUR, NOW + 2 * HOUR)

    result = my_bookings(logged_in).json()["results"][0]
    result.pop("created_at")

    assert result == {
        "id": booking.id,
        "room": {"id": room.id, "name": "Conference Room A", "capacity": 10},
        "title": "Sync",
        "start_time": "2026-10-20T13:00:00+03:00",
        "end_time": "2026-10-20T14:00:00+03:00",
        "booked_by": {"id": user.id, "username": "alice"},
    }


def test_another_users_view_never_includes_my_bookings(api_client, make_booking, bob):
    make_booking(NOW + HOUR, NOW + 2 * HOUR, title="Alice's")
    api_client.force_authenticate(bob)

    assert titles(my_bookings(api_client)) == []


def test_ordered_by_start_time_with_id_as_tie_break(logged_in, make_booking, other_room):
    late = make_booking(NOW + 5 * HOUR, NOW + 6 * HOUR, title="late")
    first = make_booking(NOW + HOUR, NOW + 2 * HOUR, title="same-start-a")
    second = make_booking(NOW + HOUR, NOW + 2 * HOUR, title="same-start-b", booking_room=other_room)

    results = my_bookings(logged_in).json()["results"]

    assert [b["id"] for b in results] == [first.id, second.id, late.id]


def test_150_upcoming_bookings_come_back_as_100_then_50(logged_in, make_booking):
    for n in range(150):
        start = NOW + timedelta(days=1, minutes=30 * n)
        make_booking(start, start + timedelta(minutes=15), title=f"b{n:03d}")

    first = my_bookings(logged_in).json()
    second = logged_in.get(first["next"]).json()

    assert first["count"] == 150
    assert len(first["results"]) == 100
    assert len(second["results"]) == 50
    assert second["next"] is None
    assert [b["title"] for b in first["results"] + second["results"]] == [f"b{n:03d}" for n in range(150)]


def test_page_size_above_100_is_capped(logged_in, make_booking):
    for n in range(101):
        start = NOW + timedelta(days=1, minutes=30 * n)
        make_booking(start, start + timedelta(minutes=15))

    assert len(my_bookings(logged_in, page_size=500).json()["results"]) == 100


def test_query_count_does_not_grow_with_the_number_of_bookings(logged_in, make_booking, room, other_room):
    def queries_for(count, booking_room):
        for n in range(count):
            start = NOW + timedelta(days=2 + (booking_room.id % 2) * 10, hours=n)
            make_booking(start, start + timedelta(minutes=30), booking_room=booking_room)
        with CaptureQueriesContext(connection) as ctx:
            assert my_bookings(logged_in).status_code == 200
        return len(ctx.captured_queries)

    assert queries_for(5, room) == queries_for(45, other_room)


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"mine": "false"}, "Use mine=true to list your own upcoming bookings."),
        ({"mine": "1"}, "Use mine=true to list your own upcoming bookings."),
        ({"mine": "true", "room": "1"}, "Use either mine=true, or room and date, not both."),
        ({"mine": "true", "date": "2026-10-20"}, "Use either mine=true, or room and date, not both."),
    ],
    ids=["mine-false", "mine-1", "mine-with-room", "mine-with-date"],
)
def test_bad_mine_filters_are_a_validation_error(logged_in, params, message):
    response = logged_in.get("/api/bookings/", params)

    assert response.status_code == 400
    assert response.json()["error"]["fields"] == {"mine": [message]}
