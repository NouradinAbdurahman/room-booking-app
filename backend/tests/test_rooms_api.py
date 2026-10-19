"""Seam 1: GET /api/rooms/ over HTTP against PostgreSQL."""

import pytest

from rooms.models import Room

pytestmark = pytest.mark.django_db


@pytest.fixture
def logged_in(api_client, user):
    api_client.force_authenticate(user)
    return api_client


def test_logged_out_user_gets_401(api_client):
    response = api_client.get("/api/rooms/")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_lists_rooms_ordered_by_name_in_the_agreed_shape(logged_in):
    Room.objects.create(name="Meeting Room B", capacity=6)
    Room.objects.create(name="Conference Room A", capacity=10)
    Room.objects.create(name="Focus Room", capacity=4)

    response = logged_in.get("/api/rooms/")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert body["next"] is None
    assert body["previous"] is None
    assert [room["name"] for room in body["results"]] == [
        "Conference Room A",
        "Focus Room",
        "Meeting Room B",
    ]
    assert set(body["results"][0]) == {"id", "name", "capacity"}
    assert body["results"][0]["capacity"] == 10


def test_page_size_is_capped_at_100(logged_in):
    Room.objects.bulk_create(Room(name=f"Room {n:03d}", capacity=2) for n in range(105))

    response = logged_in.get("/api/rooms/", {"page_size": 500})

    body = response.json()
    assert body["count"] == 105
    assert len(body["results"]) == 100
    assert body["next"] is not None


def test_small_pages_cover_every_room_exactly_once(logged_in):
    Room.objects.bulk_create(Room(name=f"Room {n:02d}", capacity=2) for n in range(7))

    seen, url, params = [], "/api/rooms/", {"page_size": 3}
    while url:
        body = logged_in.get(url, params).json()
        seen += [room["name"] for room in body["results"]]
        url, params = body["next"], None

    assert seen == [f"Room {n:02d}" for n in range(7)]
