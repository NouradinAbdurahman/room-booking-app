"""Ticket 12: every error from every endpoint uses one envelope (ADR 0006).

    {"error": {"code": "...", "message": "...", "fields": {...}}}

One row per endpoint and failure, so a gap shows up as a single failing case.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bookings import services
from tests.helpers import PASSWORD, csrf_token, login

pytestmark = pytest.mark.django_db

DOHA = ZoneInfo("Asia/Qatar")
NOW = datetime(2026, 10, 20, 8, tzinfo=DOHA)


@pytest.fixture(autouse=True)
def fixed_clock(server_clock):
    server_clock(NOW)


def assert_envelope(response, status, code):
    assert response.status_code == status, response.content
    assert response["Content-Type"].startswith("application/json")
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert set(error) == {"code", "message", "fields"}
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"].strip()
    assert isinstance(error["fields"], dict)
    return error


def booking_body(room, **overrides):
    body = {
        "room_id": room.id,
        "title": "Sync",
        "start_time": "2026-10-20T10:00:00+03:00",
        "end_time": "2026-10-20T11:00:00+03:00",
    }
    return {**body, **overrides}


# ---- 400 validation_error / invalid_credentials ---------------------------------


def test_400_booking_validation(logged_in, room):
    error = assert_envelope(
        logged_in.post("/api/bookings/", booking_body(room, title=""), format="json"), 400, "validation_error"
    )
    assert error["fields"] == {"title": ["This field may not be blank."]}


def test_400_day_filter(logged_in):
    assert_envelope(logged_in.get("/api/bookings/", {"room": "x", "date": "y"}), 400, "validation_error")


def test_400_malformed_json(logged_in):
    response = logged_in.post("/api/bookings/", data="{nope", content_type="application/json")
    assert assert_envelope(response, 400, "validation_error")["message"] == "The request body is not valid JSON."


def test_400_invalid_credentials(api_client, user):
    assert_envelope(login(api_client, csrf_token(api_client), password="wrong"), 400, "invalid_credentials")


# ---- 401 / 403 -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/auth/me/"),
        ("post", "/api/auth/logout/"),
        ("get", "/api/rooms/"),
        ("get", "/api/bookings/?mine=true"),
        ("post", "/api/bookings/"),
        ("delete", "/api/bookings/1/"),
    ],
)
def test_401_not_authenticated(api_client, method, url):
    response = getattr(api_client, method)(url)
    assert_envelope(response, 401, "not_authenticated")
    assert response["WWW-Authenticate"] == "Session"


def test_403_csrf_failed(api_client, user, room):
    login(api_client, csrf_token(api_client))
    assert_envelope(api_client.post("/api/bookings/", booking_body(room), format="json"), 403, "csrf_failed")


def test_403_not_booker(logged_in, make_booking, room):
    bob = get_user_model().objects.create_user("bob")
    booking = make_booking(datetime(2026, 10, 20, 10, tzinfo=DOHA), datetime(2026, 10, 20, 11, tzinfo=DOHA), booker=bob)
    assert_envelope(logged_in.delete(f"/api/bookings/{booking.id}/"), 403, "not_booker")


# ---- 404 / 405 / 409 / 415 / 429 ------------------------------------------------------


def test_404_unknown_booking(logged_in):
    assert_envelope(logged_in.delete("/api/bookings/999999/"), 404, "not_found")


def test_404_unknown_api_url(logged_in):
    assert_envelope(logged_in.get("/api/nothing-here/"), 404, "not_found")


def test_404_page_out_of_range(logged_in):
    assert_envelope(logged_in.get("/api/rooms/", {"page": 99}), 404, "not_found")


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/auth/login/"),
        ("get", "/api/auth/logout/"),
        ("post", "/api/auth/me/"),
        ("post", "/api/rooms/"),
        ("put", "/api/bookings/1/"),
        ("patch", "/api/bookings/1/"),
        ("delete", "/api/bookings/"),
    ],
)
def test_405_method_not_allowed(logged_in, method, url):
    assert_envelope(getattr(logged_in, method)(url), 405, "method_not_allowed")


def test_409_booking_conflict(logged_in, room):
    assert logged_in.post("/api/bookings/", booking_body(room), format="json").status_code == 201
    assert_envelope(logged_in.post("/api/bookings/", booking_body(room), format="json"), 409, "booking_conflict")


def test_415_form_encoded_body(logged_in, room):
    response = logged_in.post("/api/bookings/", booking_body(room), format="multipart")
    assert_envelope(response, 415, "unsupported_media_type")


def test_429_throttled_login(api_client, user):
    token = csrf_token(api_client)
    for _ in range(5):
        login(api_client, token, password="wrong")
    response = login(api_client, token, password="wrong")
    error = assert_envelope(response, 429, "throttled")
    assert error["message"].startswith("Too many login attempts. Try again in ")
    assert int(response["Retry-After"]) > 0


# ---- 500 --------------------------------------------------------------------


def test_500_unexpected_error_still_uses_the_envelope_and_hides_details(user, room, monkeypatch):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)

    def explode(**kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(services, "create_booking", explode)

    error = assert_envelope(client.post("/api/bookings/", booking_body(room), format="json"), 500, "server_error")
    assert "secret" not in error["message"]
