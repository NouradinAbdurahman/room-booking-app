import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from accounts.management.commands.seed_demo import DEMO_USERNAMES
from tests.helpers import csrf_token, login

pytestmark = pytest.mark.django_db

DEMO_PASSWORD = "demo-password-for-tests"


@pytest.fixture(autouse=True)
def _demo_password(settings):
    settings.DEMO_USER_PASSWORD = DEMO_PASSWORD


@pytest.mark.parametrize("username", DEMO_USERNAMES)
def test_seeded_demo_users_can_log_in(api_client, username):
    call_command("seed_demo")

    assert login(api_client, csrf_token(api_client), username, DEMO_PASSWORD).status_code == 200


def test_seeding_twice_is_idempotent_and_stores_only_hashes(api_client):
    call_command("seed_demo")
    call_command("seed_demo")

    # "Passwords are stored hashed" is not observable over HTTP, so check storage directly.
    stored = get_user_model().objects.filter(username__in=DEMO_USERNAMES).values_list("password", flat=True)
    assert stored and all(DEMO_PASSWORD not in p for p in stored)
    assert login(api_client, csrf_token(api_client), "user1", DEMO_PASSWORD).status_code == 200


def test_seeding_without_a_demo_password_fails_loudly(settings):
    settings.DEMO_USER_PASSWORD = ""

    with pytest.raises(CommandError, match="DEMO_USER_PASSWORD"):
        call_command("seed_demo")


def test_seed_creates_the_three_demo_rooms_once(api_client):
    call_command("seed_demo")
    call_command("seed_demo")
    login(api_client, csrf_token(api_client), "user1", DEMO_PASSWORD)

    rooms = api_client.get("/api/rooms/").json()

    assert rooms["count"] == 3
    assert [(r["name"], r["capacity"]) for r in rooms["results"]] == [
        ("Conference Room A", 10),
        ("Focus Room", 4),
        ("Meeting Room B", 6),
    ]
