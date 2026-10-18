import pytest

from tests.helpers import csrf_token, login

pytestmark = pytest.mark.django_db


def test_unknown_api_url_gets_404_envelope(api_client, user):
    api_client.force_authenticate(user)

    response = api_client.get("/api/no-such-thing/")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Not found.", "fields": {}}
    }


def test_malformed_json_body_gets_plain_english_validation_error(api_client, db):
    response = api_client.post(
        "/api/auth/login/",
        data="{not json",
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token(api_client),
    )

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "validation_error",
        "message": "The request body is not valid JSON.",
        "fields": {},
    }


def test_csrf_token_echoed_in_body_authorises_login(api_client, user):
    body_token = api_client.get("/api/auth/csrf/").json()["csrf_token"]

    assert login(api_client, body_token).status_code == 200
