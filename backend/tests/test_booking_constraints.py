"""Seam 2: PostgreSQL itself rejects invalid Bookings and Double-bookings, even
when no validation runs (ADRs 0001-0003). Each refusal is checked by the name
of the constraint that fired, so the right rule is proven, not just "an error"."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from bookings.models import Booking
from rooms.models import Room

pytestmark = pytest.mark.django_db

DOHA = ZoneInfo("Asia/Qatar")
EXCLUSION_VIOLATION = "23P01"


def doha(hour, minute=0, day=20):
    return datetime(2026, 10, day, hour, minute, tzinfo=DOHA)


@pytest.fixture
def room(db):
    return Room.objects.create(name="Conference Room A", capacity=10)


@pytest.fixture
def other_room(db):
    return Room.objects.create(name="Focus Room", capacity=4)


@pytest.fixture
def book(room, user):
    """Write a Booking straight to the database, skipping every validation."""

    def _book(start, end, *, booking_room=None, title="Team Sync", **extra):
        return Booking.objects.create(
            room=booking_room or room, user=user, title=title, start_time=start, end_time=end, **extra
        )

    return _book


def refused_by(create, *args, **kwargs):
    """Assert PostgreSQL refuses the write; return its diagnostics (constraint name, SQLSTATE)."""
    with pytest.raises(IntegrityError) as excinfo, transaction.atomic():
        create(*args, **kwargs)
    return excinfo.value.__cause__.diag


# ---- Double-booking (exclusion constraint) --------------------------------


def test_overlapping_active_booking_in_same_room_is_refused_by_the_exclusion_constraint(book):
    book(doha(10), doha(11))

    diag = refused_by(book, doha(10, 30), doha(11, 30))

    assert diag.constraint_name == "no_overlapping_active_bookings"
    assert diag.sqlstate == EXCLUSION_VIOLATION


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (doha(10), doha(11)),  # identical
        (doha(9), doha(12)),  # contains it
        (doha(10, 15), doha(10, 45)),  # inside it
        (doha(9, 30), doha(10, 15)),  # overlaps its start
    ],
)
def test_every_kind_of_overlap_is_refused(book, start, end):
    book(doha(10), doha(11))

    assert refused_by(book, start, end).constraint_name == "no_overlapping_active_bookings"


def test_touching_slots_do_not_overlap(book):
    book(doha(10), doha(11))

    book(doha(11), doha(12))  # starts exactly when the first ends
    book(doha(9), doha(10))  # ends exactly when the first starts

    assert Booking.objects.count() == 3


def test_overlap_in_a_different_room_is_accepted(book, other_room):
    book(doha(10), doha(11))

    book(doha(10), doha(11), booking_room=other_room)

    assert Booking.objects.count() == 2


def test_a_cancelled_booking_does_not_occupy_its_slot(book):
    book(doha(10), doha(11), status=Booking.Status.CANCELLED, cancelled_at=timezone.now())

    book(doha(10), doha(11))

    assert Booking.objects.filter(status=Booking.Status.ACTIVE).count() == 1


def test_cancelling_frees_the_slot_for_a_new_active_booking(book):
    original = book(doha(10), doha(11))
    Booking.objects.filter(pk=original.pk).update(
        status=Booking.Status.CANCELLED, cancelled_at=timezone.now()
    )

    book(doha(10), doha(11))

    assert Booking.objects.count() == 2


# ---- Duration and ordering ------------------------------------------------


@pytest.mark.parametrize(
    "length", [timedelta(minutes=14), timedelta(hours=4, minutes=1)], ids=["14min", "4h01"]
)
def test_duration_outside_15_minutes_to_4_hours_is_refused(book, length):
    diag = refused_by(book, doha(10), doha(10) + length)

    assert diag.constraint_name == "booking_duration_15min_to_4h"


@pytest.mark.parametrize("length", [timedelta(minutes=15), timedelta(hours=4)], ids=["15min", "4h"])
def test_duration_limits_are_inclusive(book, length):
    booking = book(doha(10), doha(10) + length)

    assert Booking.objects.get(pk=booking.pk).end_time - booking.start_time == length


@pytest.mark.parametrize("end_offset", [timedelta(0), timedelta(hours=-1)], ids=["equal", "before"])
def test_end_not_after_start_is_refused(book, end_offset):
    diag = refused_by(book, doha(10), doha(10) + end_offset)

    # end <= start also breaks the 15-minute minimum, and PostgreSQL reports the
    # first failing CHECK in name order. booking_end_after_start is implied by
    # the duration rule, so it can never fire alone; it is proven to exist only
    # by test_postgresql_has_every_named_check_constraint.
    assert diag.constraint_name == "booking_duration_15min_to_4h"


def test_booking_may_cross_midnight(book):
    book(doha(22), doha(1, day=21))

    assert Booking.objects.count() == 1


# ---- Title and cancellation state ---------------------------------------


@pytest.mark.parametrize("title", ["", "   ", "\t\n"])
def test_blank_title_is_refused(book, title):
    assert refused_by(book, doha(10), doha(11), title=title).constraint_name == "booking_title_not_blank"


def test_unknown_status_is_refused(book):
    diag = refused_by(book, doha(10), doha(11), status="pending")

    # "pending" also breaks the status/cancelled_at rule, which PostgreSQL checks
    # first by name. booking_status_valid is implied by that rule, so it can never
    # fire alone; it is proven to exist only by the catalog test below.
    assert diag.constraint_name == "booking_cancelled_at_matches_status"


def test_cancelled_without_cancelled_at_is_refused(book):
    diag = refused_by(book, doha(10), doha(11), status=Booking.Status.CANCELLED)

    assert diag.constraint_name == "booking_cancelled_at_matches_status"


def test_active_with_cancelled_at_is_refused(book):
    diag = refused_by(book, doha(10), doha(11), cancelled_at=timezone.now())

    assert diag.constraint_name == "booking_cancelled_at_matches_status"


# ---- The constraint as PostgreSQL actually has it -------------------------


def test_postgresql_has_the_active_only_gist_exclusion_constraint():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.contype, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'bookings_booking' AND c.conname = 'no_overlapping_active_bookings'
            """
        )
        contype, definition = cursor.fetchone()
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'")
        has_btree_gist = cursor.fetchone() is not None

    assert connection.pg_version >= 170000  # PostgreSQL 17, as pinned (ADR 0007)
    assert contype == "x"  # an exclusion constraint
    assert has_btree_gist
    assert definition.startswith("EXCLUDE USING gist (room_id WITH =, tstzrange(start_time, end_time, '[)'::text) WITH &&)")
    assert definition.endswith("WHERE (((status)::text = 'active'::text))")


def test_postgresql_has_every_named_check_constraint():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'bookings_booking' AND c.contype = 'c'
            """
        )
        checks = dict(cursor.fetchall())

    assert checks == {
        "booking_end_after_start": "CHECK ((end_time > start_time))",
        "booking_duration_15min_to_4h": (
            "CHECK (((end_time >= (start_time + '00:15:00'::interval)) "
            "AND (end_time <= (start_time + '04:00:00'::interval))))"
        ),
        "booking_title_not_blank": "CHECK ((NOT ((title)::text ~ '^\\s*$'::text)))",
        "booking_status_valid": (
            "CHECK (((status)::text = ANY ((ARRAY['active'::character varying, "
            "'cancelled'::character varying])::text[])))"
        ),
        "booking_cancelled_at_matches_status": (
            "CHECK (((((status)::text = 'cancelled'::text) AND (cancelled_at IS NOT NULL)) "
            "OR (((status)::text = 'active'::text) AND (cancelled_at IS NULL))))"
        ),
    }


def test_postgresql_has_exactly_the_specified_indexes():
    with connection.cursor() as cursor:
        cursor.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'bookings_booking'")
        indexes = {name for (name,) in cursor.fetchall()}

    # Spec §2: the exclusion constraint's GiST index and two partial btrees; no others.
    assert indexes == {
        "bookings_booking_pkey",
        "no_overlapping_active_bookings",
        "booking_room_start_active_idx",
        "booking_user_start_active_idx",
    }
