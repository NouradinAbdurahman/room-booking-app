"""The two Booking list queries, exactly as the API runs them (ADRs 0005, 0006).

Kept in one place so the view and the EXPLAIN evidence command
(manage.py explain_booking_queries) always measure the same SQL.

Both add a lower bound on start_time of "MAX_DURATION before" the window.
It changes no result: the database guarantees no Booking lasts longer than
MAX_DURATION (booking_duration_15min_to_4h), so a Booking that starts earlier
has ended before the window opens. It lets the (room_id|user_id, start_time)
index skip all older history, so the cost stays flat as history grows
(evidence: .scratch/room-booking-app/evidence/13-performance.md).
"""

from .doha_time import doha_day_bounds
from .models import MAX_DURATION, Booking, BookingStatus


def day_schedule(room, date):
    """Every Active booking overlapping one Doha Day for a Room, in start order."""
    day_start, day_end = doha_day_bounds(date)
    # Overlap, not "starts on": a Booking crossing midnight shows on both Days.
    return _listed(
        Booking.objects.filter(
            room=room,
            start_time__gt=day_start - MAX_DURATION,
            start_time__lt=day_end,
            end_time__gt=day_start,
        )
    )


def upcoming_bookings(user, now):
    """A User's Upcoming bookings: Active and not yet ended, in start order."""
    return _listed(Booking.objects.filter(user=user, start_time__gt=now - MAX_DURATION, end_time__gt=now))


def _listed(bookings):
    return (
        bookings.filter(status=BookingStatus.ACTIVE)
        .select_related("room", "user")  # no query per row
        .order_by("start_time", "id")
    )
