"""The booking rules, in the order spec §5 fixes (steps 2-7; step 1, the
request's shape, is the serializer's job). Correctness of the no-overlap rule
never depends on the pre-check: PostgreSQL's exclusion constraint decides,
including when two requests arrive at the same moment (ADR 0001)."""

from django.db import IntegrityError, OperationalError, transaction
from django.utils import timezone
from rest_framework import exceptions, status

from rooms.models import Room

from .models import MAX_DURATION, MIN_DURATION, OVERLAP_CONSTRAINT, Booking, BookingStatus

EXCLUSION_VIOLATION = "23P01"
DEADLOCK_DETECTED = "40P01"
# Two truly simultaneous overlapping inserts can deadlock inside PostgreSQL's
# exclusion check; PostgreSQL then aborts one of them. A deadlock is transient
# by definition, so the insert is retried: the retry either meets the other,
# now committed, Booking (23P01, so 409) or finds the Slot free (201).
INSERT_ATTEMPTS = 3


class BookingConflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "booking_conflict"
    default_detail = "This room is already booked at that time."


def current_time():
    """The server clock, the only clock the rules trust (ADR 0003)."""
    return timezone.now()


def create_booking(*, booker, room_id, title, start_time, end_time):
    room = _existing_room(room_id)  # step 2
    _check_times(start_time, end_time)  # steps 3-5

    conflicting = _overlapping_booking(room, start_time, end_time)  # step 6: a friendly message only
    if conflicting:
        raise BookingConflict(_conflict_message(room, conflicting))

    # Step 7: the database decides. Every pass returns or raises; the last
    # attempt re-raises a deadlock, so the loop never falls through.
    for attempt in range(1, INSERT_ATTEMPTS + 1):
        try:
            with transaction.atomic():
                return Booking.objects.create(
                    room=room, user=booker, title=title, start_time=start_time, end_time=end_time
                )
        except IntegrityError as error:
            if not is_overlap_violation(error):
                raise
            conflicting = _overlapping_booking(room, start_time, end_time)
            raise BookingConflict(_conflict_message(room, conflicting)) from error
        except OperationalError as error:
            if not is_deadlock(error) or attempt == INSERT_ATTEMPTS:
                raise


class NotBooker(exceptions.PermissionDenied):
    default_code = "not_booker"
    default_detail = "You can only cancel your own bookings."


class NoActiveBooking(exceptions.NotFound):
    default_detail = "This booking is already cancelled or does not exist."


def cancel_booking(*, booker, booking_id):
    """Cancel one of the Booker's Active bookings (ADR 0002).

    A single conditional UPDATE marks it cancelled and keeps the row, so the
    Slot is freed and the history stays. There is no time limit: the brief's
    only rule is that the Booker cancels.
    """
    now = current_time()
    # .update() skips auto_now, so updated_at is set here explicitly.
    updated_rows = Booking.objects.filter(
        pk=booking_id, user=booker, status=BookingStatus.ACTIVE
    ).update(status=BookingStatus.CANCELLED, cancelled_at=now, updated_at=now)
    if updated_rows:
        return
    if Booking.objects.filter(pk=booking_id, status=BookingStatus.ACTIVE).exists():
        raise NotBooker()
    raise NoActiveBooking()


def is_overlap_violation(error):
    """True only for PostgreSQL's exclusion violation on the no-overlap constraint (ADR 0001)."""
    cause = error.__cause__
    diag = getattr(cause, "diag", None)
    return (
        getattr(cause, "sqlstate", None) == EXCLUSION_VIOLATION
        and getattr(diag, "constraint_name", None) == OVERLAP_CONSTRAINT
    )


def is_deadlock(error):
    """True for PostgreSQL's deadlock (40P01): transient, so safe to retry."""
    return getattr(error.__cause__, "sqlstate", None) == DEADLOCK_DETECTED


def _existing_room(room_id):
    try:
        return Room.objects.get(pk=room_id)
    except Room.DoesNotExist:
        raise exceptions.ValidationError({"room_id": ["No Room has this id."]}) from None


def _check_times(start, end):
    if end <= start:
        raise exceptions.ValidationError({"end_time": ["End time must be after the start time."]})
    if not MIN_DURATION <= end - start <= MAX_DURATION:
        raise exceptions.ValidationError(
            {"end_time": ["A booking must last at least 15 minutes and at most 4 hours."]}
        )
    if start < current_time():
        raise exceptions.ValidationError({"start_time": ["A booking cannot start in the past."]})


def _overlapping_booking(room, start, end):
    return (
        Booking.objects.filter(
            room=room, status=BookingStatus.ACTIVE, start_time__lt=end, end_time__gt=start
        )
        .order_by("start_time")
        .first()
    )


def _conflict_message(room, conflicting):
    if conflicting is None:  # the conflicting Booking was cancelled again in the meantime
        return f"{room.name} is already booked at that time."
    start = timezone.localtime(conflicting.start_time)
    end = timezone.localtime(conflicting.end_time)
    return f"{room.name} is already booked {start:%H:%M}–{end:%H:%M}."
