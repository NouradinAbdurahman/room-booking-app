"""Seam 1: DELETE /api/bookings/{id}/ over HTTP against PostgreSQL (ADR 0002)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model

from bookings.models import Booking, BookingStatus

pytestmark = pytest.mark.django_db

DOHA = ZoneInfo("Asia/Qatar")
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=DOHA)


@pytest.fixture(autouse=True)
def fixed_clock(server_clock):
    server_clock(NOW)


@pytest.fixture
def bob(db):
    return get_user_model().objects.create_user(username="bob")


@pytest.fixture
def make_booking(room, user):
    def _make(start=NOW + timedelta(hours=2), length=timedelta(hours=1), booker=None, title="Sync", **extra):
        return Booking.objects.create(
            room=room, user=booker or user, title=title, start_time=start, end_time=start + length, **extra
        )

    return _make


def cancel(client, booking_id):
    return client.delete(f"/api/bookings/{booking_id}/")


def test_booker_cancels_and_the_row_is_kept_as_cancelled(logged_in, make_booking):
    booking = make_booking()

    response = cancel(logged_in, booking.id)

    assert response.status_code == 204
    assert response.content == b""
    booking.refresh_from_db()
    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancelled_at == NOW
    assert booking.updated_at >= booking.created_at


def test_cancelled_slot_can_be_booked_again(logged_in, make_booking, room):
    booking = make_booking()
    assert cancel(logged_in, booking.id).status_code == 204

    response = logged_in.post(
        "/api/bookings/",
        {
            "room_id": room.id,
            "title": "Rebooked",
            "start_time": booking.start_time.isoformat(),
            "end_time": booking.end_time.isoformat(),
        },
        format="json",
    )

    assert response.status_code == 201
    assert Booking.objects.filter(room=room, start_time=booking.start_time).count() == 2  # history kept


def test_cancelled_booking_leaves_the_day_schedule(logged_in, make_booking, room):
    booking = make_booking(title="Gone")
    cancel(logged_in, booking.id)

    response = logged_in.get("/api/bookings/", {"room": room.id, "date": "2026-10-20"})

    assert response.json()["results"] == []


def test_someone_elses_booking_cannot_be_cancelled(logged_in, make_booking, bob):
    booking = make_booking(booker=bob)

    response = cancel(logged_in, booking.id)

    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "not_booker",
        "message": "You can only cancel your own bookings.",
        "fields": {},
    }
    booking.refresh_from_db()
    assert booking.status == BookingStatus.ACTIVE and booking.cancelled_at is None


def test_cancelling_twice_is_a_404(logged_in, make_booking):
    booking = make_booking()
    assert cancel(logged_in, booking.id).status_code == 204

    response = cancel(logged_in, booking.id)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    booking.refresh_from_db()
    assert booking.cancelled_at == NOW, "the first cancellation is not overwritten"


def test_someone_elses_cancelled_booking_is_a_404_not_a_403(logged_in, make_booking, bob):
    booking = make_booking(booker=bob, status=BookingStatus.CANCELLED, cancelled_at=NOW)

    assert cancel(logged_in, booking.id).status_code == 404


def test_unknown_booking_is_a_404(logged_in):
    response = cancel(logged_in, 999999)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    ("start", "label"),
    [(NOW - timedelta(minutes=30), "in progress"), (NOW - timedelta(days=1), "already ended")],
    ids=["started", "ended"],
)
def test_booker_may_cancel_a_booking_that_has_started_or_ended(logged_in, make_booking, start, label):
    booking = make_booking(start=start)

    assert cancel(logged_in, booking.id).status_code == 204, label


@pytest.mark.parametrize("method", ["put", "patch", "get"])
def test_other_methods_on_a_booking_are_405(logged_in, make_booking, method):
    booking = make_booking()

    response = getattr(logged_in, method)(f"/api/bookings/{booking.id}/", {}, format="json")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
    booking.refresh_from_db()
    assert booking.status == BookingStatus.ACTIVE


def test_logged_out_user_gets_401(api_client, make_booking):
    booking = make_booking()

    response = cancel(api_client, booking.id)

    assert response.status_code == 401
    booking.refresh_from_db()
    assert booking.status == BookingStatus.ACTIVE
