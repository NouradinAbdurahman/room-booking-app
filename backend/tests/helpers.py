PASSWORD = "correct-horse-battery"


def csrf_token(client):
    """Fetch the CSRF cookie the way the SPA does on start-up."""
    response = client.get("/api/auth/csrf/")
    assert response.status_code == 200
    return client.cookies["csrftoken"].value


def login(client, token, username="alice", password=PASSWORD):
    """POST credentials to login; pass token=None to send no CSRF header."""
    headers = {} if token is None else {"HTTP_X_CSRFTOKEN": token}
    return client.post(
        "/api/auth/login/",
        {"username": username, "password": password},
        format="json",
        **headers,
    )
