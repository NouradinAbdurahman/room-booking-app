import pytest

from bookings.models import Booking
from tests.helpers import PASSWORD, csrf_token, login

pytestmark = pytest.mark.django_db

PROTECTED_ENDPOINTS = [
    ("get", "/api/auth/me/"),
    ("post", "/api/auth/logout/"),
    ("get", "/api/rooms/"),
    ("get", "/api/bookings/?room=1&date=2030-01-15"),
    ("post", "/api/bookings/"),
    ("delete", "/api/bookings/1/"),
]



def book(client, room, token=None):
    """The authenticated unsafe request used by the CSRF tests (spec T-AUTH-2/3/5)."""
    headers = {} if token is None else {"HTTP_X_CSRFTOKEN": token}
    return client.post(
        "/api/bookings/",
        {
            "room_id": room.id,
            "title": "Sync",
            "start_time": "2030-01-15T10:00:00+03:00",
            "end_time": "2030-01-15T11:00:00+03:00",
        },
        format="json",
        **headers,
    )


@pytest.mark.parametrize(("method", "url"), PROTECTED_ENDPOINTS)
def test_logged_out_request_gets_401_with_envelope_and_session_challenge(api_client, method, url):
    response = getattr(api_client, method)(url)

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Session"
    assert response.json()["error"]["code"] == "not_authenticated"
    assert response.json()["error"]["message"]
    assert response.json()["error"]["fields"] == {}


def test_bootstrap_login_rotates_token_and_new_token_authorises_unsafe_request(api_client, user, room):
    bootstrap_token = csrf_token(api_client)

    response = login(api_client, bootstrap_token)

    assert response.status_code == 200
    assert response.json() == {"user": {"id": user.id, "username": "alice"}}
    rotated_token = api_client.cookies["csrftoken"].value
    assert rotated_token != bootstrap_token
    assert api_client.get("/api/auth/me/").json() == {"id": user.id, "username": "alice"}

    assert book(api_client, room, rotated_token).status_code == 201


def test_stale_pre_login_token_is_refused_after_login(api_client, user, room):
    bootstrap_token = csrf_token(api_client)
    assert login(api_client, bootstrap_token).status_code == 200

    response = book(api_client, room, bootstrap_token)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert not Booking.objects.exists(), "refused request must create no Booking"
    assert api_client.get("/api/auth/me/").status_code == 200


@pytest.mark.parametrize("token", [None, "wrong-token-wrong-token-wrong-token-wrong-token-wro"])
def test_login_without_valid_csrf_token_is_refused_even_with_correct_credentials(
    api_client, user, token
):
    csrf_token(api_client)

    response = login(api_client, token)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert api_client.get("/api/auth/me/").status_code == 401, "no session may be created"


def test_authenticated_unsafe_request_without_token_is_refused(api_client, user, room):
    assert login(api_client, csrf_token(api_client)).status_code == 200

    booking = book(api_client, room)
    logout = api_client.post("/api/auth/logout/")

    for response in (booking, logout):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "csrf_failed"
    assert not Booking.objects.exists(), "refused request must create no Booking"
    assert api_client.get("/api/auth/me/").status_code == 200, "refused logout must keep the session"


@pytest.mark.parametrize(
    ("username", "password"), [("alice", "not-the-password"), ("nobody", PASSWORD)]
)
def test_wrong_credentials_get_one_message_that_does_not_reveal_whether_user_exists(
    api_client, user, username, password
):
    response = login(api_client, csrf_token(api_client), username=username, password=password)

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "invalid_credentials",
        "message": "Invalid username or password.",
        "fields": {},
    }


def test_login_with_missing_fields_is_a_validation_error(api_client, db):
    response = api_client.post(
        "/api/auth/login/", {}, format="json", HTTP_X_CSRFTOKEN=csrf_token(api_client)
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert set(error["fields"]) == {"username", "password"}


def test_sixth_login_attempt_within_a_minute_is_throttled(api_client, user):
    token = csrf_token(api_client)
    for _ in range(5):
        assert login(api_client, token, password="wrong").status_code == 400

    response = login(api_client, token, password="wrong")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "throttled"


def test_logout_ends_the_session(api_client, user):
    login(api_client, csrf_token(api_client))

    response = api_client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=api_client.cookies["csrftoken"].value)

    assert response.status_code == 204
    assert api_client.get("/api/auth/me/").status_code == 401


def attempts_from(api_client, forwarded_for, count):
    """Failed logins arriving via the Vite proxy, which appends the browser's address."""
    token = csrf_token(api_client)
    return [
        login(api_client, token, password="wrong", HTTP_X_FORWARDED_FOR=forwarded_for).status_code
        for _ in range(count)
    ]


def test_each_client_behind_the_proxy_has_its_own_login_limit(api_client, user):
    assert attempts_from(api_client, "203.0.113.1", 6)[-1] == 429

    assert attempts_from(api_client, "203.0.113.2", 1) == [400]


def test_spoofed_address_in_front_of_the_proxy_entry_does_not_dodge_the_limit(api_client, user):
    attempts_from(api_client, "203.0.113.1", 5)

    # A client can prepend anything; the proxy's own (last) entry is what counts.
    assert attempts_from(api_client, "198.51.100.9, 203.0.113.1", 1) == [429]
