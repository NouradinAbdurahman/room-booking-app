"""Seam 2: PostgreSQL itself rejects invalid Rooms, even when no validation runs."""

import pytest
from django.db import IntegrityError, transaction

from rooms.models import Room

pytestmark = pytest.mark.django_db


def rejected_by_database(**fields):
    with pytest.raises(IntegrityError), transaction.atomic():
        Room.objects.create(**fields)


def test_duplicate_room_name_is_rejected():
    Room.objects.create(name="Focus Room", capacity=4)

    rejected_by_database(name="Focus Room", capacity=8)


@pytest.mark.parametrize("capacity", [0, -3])
def test_capacity_that_is_not_positive_is_rejected(capacity):
    rejected_by_database(name="Broom Cupboard", capacity=capacity)


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_room_name_is_rejected(name):
    rejected_by_database(name=name, capacity=4)


def test_valid_room_is_accepted():
    room = Room.objects.create(name="Conference Room A", capacity=10)

    assert Room.objects.get(pk=room.pk).capacity == 10
