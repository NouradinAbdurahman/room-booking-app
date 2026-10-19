"""Seam 1: POST /api/bookings/ over HTTP against PostgreSQL (spec §4, §5; ADRs 0001, 0003, 0005)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from bookings.models import Booking
from rooms.models import Room

pytestmark = pytest.mark.django_db

DOHA = ZoneInfo("Asia/Qatar")
NOW = datetime(2026, 10, 20, 8, 30, tzinfo=DOHA)  # the server clock in these tests


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr("bookings.services.current_time", lambda: NOW)


@pytest.fixture
def room(db):
    return Room.objects.create(name="Conference Room A", capacity=10)


@pytest.fixture
def other_room(db):
    return Room.objects.create(name="Focus Room", capacity=4)


@pytest.fixture
def logged_in(api_client, user):
    api_client.force_authenticate(user)
    return api_client


def payload(room, start="2026-10-20T10:00:00+03:00", end="2026-10-20T11:00:00+03:00", title="Product Review", **overrides):
    body = {"room_id": room.id, "title": title, "start_time": start, "end_time": end}
    body.update(overrides)
    return body


def post(client, body):
    return client.post("/api/bookings/", body, format="json")


def error_of(response):
    return response.json()["error"]


# ---- Success ----------------------------------------------------------------


def test_valid_booking_is_created_for_the_session_user(logged_in, room, user):
    response = post(logged_in, payload(room))

    assert response.status_code == 201
    body = response.json()
    created_at = body.pop("created_at")
    assert body == {
        "id": body["id"],
        "room": {"id": room.id, "name": "Conference Room A", "capacity": 10},
        "title": "Product Review",
        "start_time": "2026-10-20T10:00:00+03:00",
        "end_time": "2026-10-20T11:00:00+03:00",
        "booked_by": {"id": user.id, "username": "alice"},
    }
    assert created_at.endswith("+03:00")
    assert Booking.objects.get(pk=body["id"]).user == user


def test_times_sent_in_another_offset_mean_the_same_instant(logged_in, room):
    response = post(logged_in, payload(room, start="2026-10-20T07:00:00Z", end="2026-10-20T08:00:00+00:00"))

    assert response.status_code == 201
    assert response.json()["start_time"] == "2026-10-20T10:00:00+03:00"


def test_booking_crossing_midnight_is_accepted(logged_in, room):
    response = post(logged_in, payload(room, start="2026-10-20T22:00:00+03:00", end="2026-10-21T01:00:00+03:00"))

    assert response.status_code == 201


def test_title_is_trimmed(logged_in, room):
    assert post(logged_in, payload(room, title="  Sync  ")).json()["title"] == "Sync"


# ---- Duration limits ---------------------------------------------------------


@pytest.mark.parametrize(
    ("end", "accepted"),
    [
        ("2026-10-20T10:15:00+03:00", True),  # exactly 15 minutes
        ("2026-10-20T14:00:00+03:00", True),  # exactly 4 hours
        ("2026-10-20T10:14:00+03:00", False),  # 14 minutes
        ("2026-10-20T14:01:00+03:00", False),  # 4 hours 1 minute
    ],
    ids=["15min", "4h", "14min", "4h01"],
)
def test_duration_must_be_15_minutes_to_4_hours_inclusive(logged_in, room, end, accepted):
    response = post(logged_in, payload(room, end=end))

    if accepted:
        assert response.status_code == 201
    else:
        assert response.status_code == 400
        assert error_of(response)["code"] == "validation_error"
        assert set(error_of(response)["fields"]) == {"end_time"}


@pytest.mark.parametrize("end", ["2026-10-20T10:00:00+03:00", "2026-10-20T09:00:00+03:00"], ids=["equal", "before"])
def test_end_must_be_after_start(logged_in, room, end):
    response = post(logged_in, payload(room, end=end))

    assert response.status_code == 400
    assert error_of(response)["fields"] == {"end_time": ["End time must be after the start time."]}


# ---- Not in the past (server clock) -------------------------------------------


def test_start_in_the_past_is_refused(logged_in, room):
    response = post(logged_in, payload(room, start="2026-10-20T08:29:00+03:00", end="2026-10-20T09:00:00+03:00"))

    assert response.status_code == 400
    assert error_of(response)["fields"] == {"start_time": ["A booking cannot start in the past."]}


def test_start_exactly_now_is_allowed(logged_in, room):
    response = post(logged_in, payload(room, start="2026-10-20T08:30:00+03:00", end="2026-10-20T09:00:00+03:00"))

    assert response.status_code == 201


# ---- Shape ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"start_time": "2026-10-20T10:00:00"}, "start_time"),  # no offset
        ({"end_time": "2026-10-20 11:00"}, "end_time"),  # no offset
        ({"start_time": "2026-10-20T10:00:30+03:00"}, "start_time"),  # seconds
        ({"end_time": "2026-10-20T11:00:00.5+03:00"}, "end_time"),  # fraction
        ({"start_time": "tomorrow"}, "start_time"),
        ({"start_time": "2026-13-01T10:00:00+03:00"}, "start_time"),
        ({"start_time": 1760943600}, "start_time"),  # not a string
        ({"title": "   "}, "title"),
        ({"title": "x" * 201}, "title"),
        ({"room_id": "abc"}, "room_id"),
    ],
    ids=[
        "no-offset",
        "no-offset-space",
        "seconds",
        "fraction",
        "words",
        "impossible-month",
        "number",
        "blank-title",
        "long-title",
        "room-not-a-number",
    ],
)
def test_badly_shaped_request_is_refused_naming_the_field(logged_in, room, overrides, field):
    response = post(logged_in, payload(room, **overrides))

    assert response.status_code == 400
    assert error_of(response)["code"] == "validation_error"
    assert set(error_of(response)["fields"]) == {field}


def test_missing_fields_are_all_reported(logged_in):
    response = post(logged_in, {})

    assert response.status_code == 400
    assert set(error_of(response)["fields"]) == {"room_id", "title", "start_time", "end_time"}


def test_unknown_room_is_refused(logged_in, room):
    response = post(logged_in, payload(room, room_id=999999))

    assert response.status_code == 400
    assert error_of(response)["fields"] == {"room_id": ["No Room has this id."]}


def test_booker_cannot_be_chosen_by_the_client(logged_in, room, user, django_user_model):
    someone_else = django_user_model.objects.create_user("mallory")

    response = post(logged_in, payload(room, user=someone_else.id, booked_by=someone_else.id))

    assert response.status_code == 201
    assert Booking.objects.get(pk=response.json()["id"]).user == user


# ---- Validation order (spec §5) ------------------------------------------------


def test_order_shape_before_room(logged_in, room):
    response = post(logged_in, payload(room, room_id=999999, start_time="2026-10-20T10:00:00"))

    assert set(error_of(response)["fields"]) == {"start_time"}


def test_order_room_before_time_rules(logged_in, room):
    response = post(logged_in, payload(room, room_id=999999, end="2026-10-20T09:00:00+03:00"))

    assert set(error_of(response)["fields"]) == {"room_id"}


def test_order_end_after_start_before_duration(logged_in, room):
    response = post(logged_in, payload(room, end="2026-10-20T09:59:00+03:00"))

    assert error_of(response)["fields"] == {"end_time": ["End time must be after the start time."]}


def test_order_duration_before_past(logged_in, room):
    response = post(logged_in, payload(room, start="2026-10-20T08:00:00+03:00", end="2026-10-20T08:05:00+03:00"))

    assert set(error_of(response)["fields"]) == {"end_time"}


def test_order_past_before_overlap(logged_in, room, user):
    Booking.objects.create(
        room=room, user=user, title="Old", start_time=datetime(2026, 10, 20, 7, tzinfo=DOHA),
        end_time=datetime(2026, 10, 20, 9, tzinfo=DOHA),
    )

    response = post(logged_in, payload(room, start="2026-10-20T08:00:00+03:00", end="2026-10-20T08:45:00+03:00"))

    assert response.status_code == 400
    assert set(error_of(response)["fields"]) == {"start_time"}


# ---- Overlap -------------------------------------------------------------------


def test_overlap_is_a_409_naming_the_room_and_the_taken_times(logged_in, room):
    assert post(logged_in, payload(room)).status_code == 201

    response = post(logged_in, payload(room, start="2026-10-20T10:30:00+03:00", end="2026-10-20T11:30:00+03:00"))

    assert response.status_code == 409
    assert error_of(response) == {
        "code": "booking_conflict",
        "message": "Conference Room A is already booked 10:00–11:00.",
        "fields": {},
    }
    assert Booking.objects.count() == 1


def test_touching_slots_are_both_accepted(logged_in, room):
    assert post(logged_in, payload(room)).status_code == 201

    assert post(logged_in, payload(room, start="2026-10-20T11:00:00+03:00", end="2026-10-20T12:00:00+03:00")).status_code == 201
    assert post(logged_in, payload(room, start="2026-10-20T09:00:00+03:00", end="2026-10-20T10:00:00+03:00")).status_code == 201


def test_same_slot_in_another_room_is_accepted(logged_in, room, other_room):
    assert post(logged_in, payload(room)).status_code == 201

    assert post(logged_in, payload(other_room)).status_code == 201


def test_a_cancelled_bookings_slot_can_be_booked(logged_in, room, user):
    Booking.objects.create(
        room=room, user=user, title="Gone", status="cancelled", cancelled_at=NOW,
        start_time=datetime(2026, 10, 20, 10, tzinfo=DOHA), end_time=datetime(2026, 10, 20, 11, tzinfo=DOHA),
    )

    assert post(logged_in, payload(room)).status_code == 201
