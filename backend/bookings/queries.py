"""The two Booking list queries, exactly as the API runs them (ADRs 0005, 0006).

Kept in one place so the view and the EXPLAIN evidence command
(manage.py explain_booking_queries) always measure the same SQL.
"""

from .doha_time import doha_day_bounds
from .models import Booking, BookingStatus


def day_schedule(room, date):
    """Every Active booking overlapping one Doha Day for a Room, in start order."""
    day_start, day_end = doha_day_bounds(date)
    # Overlap, not "starts on": a Booking crossing midnight shows on both Days.
    return _listed(Booking.objects.filter(room=room, start_time__lt=day_end, end_time__gt=day_start))


def upcoming_bookings(user, now):
    """A User's Upcoming bookings: Active and not yet ended, in start order."""
    return _listed(Booking.objects.filter(user=user, end_time__gt=now))


def _listed(bookings):
    return (
        bookings.filter(status=BookingStatus.ACTIVE)
        .select_related("room", "user")  # no query per row
        .order_by("start_time", "id")
    )
