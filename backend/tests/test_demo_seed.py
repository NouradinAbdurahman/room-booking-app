import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from tests.helpers import csrf_token, login

pytestmark = pytest.mark.django_db

DEMO_PASSWORD = "demo-password-for-tests"


@pytest.fixture(autouse=True)
def _demo_password(settings):
    settings.DEMO_USER_PASSWORD = DEMO_PASSWORD


@pytest.mark.parametrize("username", ["user1", "user2", "user3"])
def test_seeded_demo_users_can_log_in(client, username):
    call_command("seed_demo")

    assert login(client, csrf_token(client), username, DEMO_PASSWORD).status_code == 200


def test_seeding_twice_is_idempotent_and_stores_only_hashes(client):
    call_command("seed_demo")
    call_command("seed_demo")

    users = get_user_model().objects.filter(username__in=["user1", "user2", "user3"])
    assert users.count() == 3
    assert all(DEMO_PASSWORD not in u.password for u in users)
    assert login(client, csrf_token(client), "user1", DEMO_PASSWORD).status_code == 200


def test_seeding_without_a_demo_password_fails_loudly(settings):
    settings.DEMO_USER_PASSWORD = ""

    with pytest.raises(Exception, match="DEMO_USER_PASSWORD"):
        call_command("seed_demo")
