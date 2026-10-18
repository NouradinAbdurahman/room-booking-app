import pytest

from tests.helpers import PASSWORD, csrf_token, login

pytestmark = pytest.mark.django_db

PROTECTED_ENDPOINTS = [
    ("get", "/api/auth/me/"),
    ("post", "/api/auth/logout/"),
]


@pytest.mark.parametrize(("method", "url"), PROTECTED_ENDPOINTS)
def test_logged_out_request_gets_401_with_envelope_and_session_challenge(api_client, method, url):
    response = getattr(api_client, method)(url)

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Session"
    assert response.json()["error"]["code"] == "not_authenticated"
    assert response.json()["error"]["message"]
    assert response.json()["error"]["fields"] == {}


def test_bootstrap_login_rotates_token_and_new_token_authorises_unsafe_request(api_client, user):
    bootstrap_token = csrf_token(api_client)

    response = login(api_client, bootstrap_token)

    assert response.status_code == 200
    assert response.json() == {"user": {"id": user.id, "username": "alice"}}
    rotated_token = api_client.cookies["csrftoken"].value
    assert rotated_token != bootstrap_token
    assert api_client.get("/api/auth/me/").json() == {"id": user.id, "username": "alice"}

    # Until booking endpoints exist (ticket 08), logout is the authenticated unsafe request.
    response = api_client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=rotated_token)
    assert response.status_code == 204


def test_stale_pre_login_token_is_refused_after_login(api_client, user):
    bootstrap_token = csrf_token(api_client)
    assert login(api_client, bootstrap_token).status_code == 200

    response = api_client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=bootstrap_token)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert api_client.get("/api/auth/me/").status_code == 200, "refused request must change nothing"


@pytest.mark.parametrize("token", [None, "wrong-token-wrong-token-wrong-token-wrong-token-wro"])
def test_login_without_valid_csrf_token_is_refused_even_with_correct_credentials(
    api_client, user, token
):
    csrf_token(api_client)

    response = login(api_client, token)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert api_client.get("/api/auth/me/").status_code == 401, "no session may be created"


def test_authenticated_unsafe_request_without_token_is_refused(api_client, user):
    assert login(api_client, csrf_token(api_client)).status_code == 200

    response = api_client.post("/api/auth/logout/")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert api_client.get("/api/auth/me/").status_code == 200, "refused request must change nothing"


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
