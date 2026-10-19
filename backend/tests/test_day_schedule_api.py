"""Seam 1: GET /api/bookings/?room=<id>&date=YYYY-MM-DD, a Room's Doha Day schedule."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from bookings.models import Booking

pytestmark = pytest.mark.django_db

DOHA = ZoneInfo("Asia/Qatar")
DAY = "2026-10-20"


def doha(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=DOHA)





@pytest.fixture
def book(make_booking):
    def _book(start, end, title="Team Sync", **extra):
        return make_booking(start, end, title=title, **extra)

    return _book


def day_schedule(client, room, date=DAY, **params):
    return client.get("/api/bookings/", {"room": room.id, "date": date, **params})


def titles(response):
    return [b["title"] for b in response.json()["results"]]


def test_logged_out_user_gets_401(api_client, room):
    response = day_schedule(api_client, room)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_booking_is_returned_in_the_agreed_shape_in_doha_time(logged_in, book, room, user):
    booking = book(doha(20, 9), doha(20, 10))

    response = day_schedule(logged_in, room)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["next"] is None and body["previous"] is None
    result = body["results"][0]
    created_at = result.pop("created_at")
    assert result == {
        "id": booking.id,
        "room": {"id": room.id, "name": "Conference Room A", "capacity": 10},
        "title": "Team Sync",
        "start_time": "2026-10-20T09:00:00+03:00",
        "end_time": "2026-10-20T10:00:00+03:00",
        "booked_by": {"id": user.id, "username": "alice"},
    }
    assert created_at.endswith("+03:00")


def test_booking_crossing_midnight_appears_on_both_days(logged_in, book, room):
    book(doha(20, 22), doha(21, 1), title="Late Release")

    assert titles(day_schedule(logged_in, room, "2026-10-20")) == ["Late Release"]
    assert titles(day_schedule(logged_in, room, "2026-10-21")) == ["Late Release"]
    assert titles(day_schedule(logged_in, room, "2026-10-22")) == []


def test_00_30_doha_booking_is_on_its_doha_date_not_its_utc_date(logged_in, book, room):
    # 00:30 on 21 Oct in Doha is 21:30 on 20 Oct in UTC.
    book(doha(21, 0, 30), doha(21, 1, 30), title="Early Bird")

    assert titles(day_schedule(logged_in, room, "2026-10-21")) == ["Early Bird"]
    assert titles(day_schedule(logged_in, room, "2026-10-20")) == []


def test_bookings_touching_the_day_edges_belong_only_to_the_day_they_overlap(logged_in, book, room):
    book(doha(19, 23), doha(20, 0), title="Ends at midnight")
    book(doha(21, 0), doha(21, 1), title="Starts at next midnight")

    assert titles(day_schedule(logged_in, room)) == []


def test_cancelled_bookings_and_other_rooms_are_excluded(logged_in, book, room, other_room):
    book(doha(20, 9), doha(20, 10), title="Kept")
    book(doha(20, 11), doha(20, 12), title="Cancelled", status="cancelled", cancelled_at=timezone.now())
    book(doha(20, 13), doha(20, 14), title="Elsewhere", booking_room=other_room)

    assert titles(day_schedule(logged_in, room)) == ["Kept"]


def test_bookings_are_ordered_by_start_time(logged_in, book, room):
    book(doha(20, 15), doha(20, 16), title="Afternoon")
    book(doha(20, 8), doha(20, 9), title="Morning")
    book(doha(19, 23), doha(20, 1), title="From last night")

    assert titles(day_schedule(logged_in, room)) == ["From last night", "Morning", "Afternoon"]


def test_small_pages_return_every_overlapping_booking_exactly_once(logged_in, book, room):
    book(doha(19, 23), doha(20, 1), title="b00")  # crosses in from the previous Day
    for n, hour in enumerate(range(2, 22, 2), start=1):
        book(doha(20, hour), doha(20, hour, 30), title=f"b{n:02d}")
    book(doha(20, 23), doha(21, 2), title="b11")  # crosses into the next Day

    seen, url, params = [], "/api/bookings/", {"room": room.id, "date": DAY, "page_size": 3}
    while url:
        body = logged_in.get(url, params).json()
        seen += [b["title"] for b in body["results"]]
        url, params = body["next"], None

    assert seen == [f"b{n:02d}" for n in range(12)]


def test_query_count_does_not_grow_with_the_number_of_bookings(logged_in, room):
    def queries_for(count, day):
        bookers = [get_user_model().objects.create_user(f"booker-{day}-{n}") for n in range(count)]
        for n, booker in enumerate(bookers):
            Booking.objects.create(
                room=room,
                user=booker,
                title=f"Meeting {n}",
                start_time=doha(day, 0) + n * timedelta(minutes=15),
                end_time=doha(day, 0) + (n + 1) * timedelta(minutes=15),
            )
        with CaptureQueriesContext(connection) as ctx:
            response = day_schedule(logged_in, room, f"2026-10-{day}")
        assert response.json()["count"] == count
        return len(ctx.captured_queries)

    assert queries_for(5, 20) == queries_for(50, 22)


@pytest.mark.parametrize(
    ("params", "fields_with_errors"),
    [
        ({}, {"room", "date"}),
        ({"room": "ROOM"}, {"date"}),
        ({"date": DAY}, {"room"}),
        ({"room": "ROOM", "date": "20-10-2026"}, {"date"}),
        ({"room": "ROOM", "date": "2026-1-5"}, {"date"}),
        ({"room": "ROOM", "date": "2026-02-30"}, {"date"}),
        ({"room": "not-a-number", "date": DAY}, {"room"}),
        ({"room": "999999", "date": DAY}, {"room"}),
        ({"mine": "true", "room": "ROOM", "date": DAY}, {"mine"}),
    ],
    ids=[
        "no-filter",
        "room-only",
        "date-only",
        "bad-date-format",
        "date-without-leading-zeros",
        "impossible-date",
        "non-numeric-room",
        "unknown-room",
        "mixed-forms",
    ],
)
def test_bad_filters_are_a_validation_error_naming_the_field(logged_in, room, params, fields_with_errors):
    params = {k: (str(room.id) if v == "ROOM" else v) for k, v in params.items()}

    response = logged_in.get("/api/bookings/", params)

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert set(error["fields"]) == fields_with_errors
    assert all(messages for messages in error["fields"].values())


def test_unknown_room_says_so(logged_in):
    response = logged_in.get("/api/bookings/", {"room": "999999", "date": DAY})

    assert response.json()["error"]["fields"] == {"room": ["No Room has this id."]}


@pytest.mark.parametrize(
    "date",
    ["2026-10-20\n", "\u0662\u0660\u0662\u0666-\u0661\u0660-\u0662\u0660", " 2026-10-20"],
    ids=["trailing-newline", "arabic-indic-digits", "leading-space"],
)
def test_only_plain_ascii_yyyy_mm_dd_is_accepted(logged_in, room, date):
    response = logged_in.get("/api/bookings/", {"room": room.id, "date": date})

    assert response.status_code == 400
    assert set(response.json()["error"]["fields"]) == {"date"}
