from datetime import timedelta

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Func, Q

from rooms.models import Room

MIN_DURATION = timedelta(minutes=15)
MAX_DURATION = timedelta(hours=4)


class TsTzRange(Func):
    """PostgreSQL's tstzrange(start, end, '[)'): a half-open Slot, so touching Slots don't overlap."""

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class Booking(models.Model):
    """One Room reserved by one Booker for one Slot (GLOSSARY: Booking, Booker, Slot)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"

    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
    # The Booker: the User who made the Booking and the only one who may cancel it.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")
    title = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    # Cancelling keeps the row and marks it, so history stays answerable (ADR 0002).
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Every rule here is enforced by PostgreSQL, so even code that skips
        # validation cannot save an invalid Booking (ADR 0003). "Cannot start in
        # the past" is the one rule the API enforces instead.
        constraints = [
            # ADR 0001: no two Active bookings for a Room may overlap, even
            # when two requests arrive at the same moment.
            ExclusionConstraint(
                name="no_overlapping_active_bookings",
                expressions=[
                    ("room", RangeOperators.EQUAL),
                    (TsTzRange("start_time", "end_time", RangeBoundary()), RangeOperators.OVERLAPS),
                ],
                condition=Q(status="active"),
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")), name="booking_end_after_start"
            ),
            models.CheckConstraint(
                condition=Q(end_time__gte=F("start_time") + MIN_DURATION)
                & Q(end_time__lte=F("start_time") + MAX_DURATION),
                name="booking_duration_15min_to_4h",
            ),
            models.CheckConstraint(
                condition=~Q(title__regex=r"^\s*$"), name="booking_title_not_blank"
            ),
            models.CheckConstraint(
                condition=Q(status__in=["active", "cancelled"]), name="booking_status_valid"
            ),
            models.CheckConstraint(
                condition=(Q(status="cancelled") & Q(cancelled_at__isnull=False))
                | (Q(status="active") & Q(cancelled_at__isnull=True)),
                name="booking_cancelled_at_matches_status",
            ),
        ]
        indexes = [
            # A Room's Day schedule (ADR 0006).
            models.Index(
                fields=["room", "start_time"],
                condition=Q(status="active"),
                name="booking_room_start_active_idx",
            ),
            # A User's Upcoming bookings (ADR 0006).
            models.Index(
                fields=["user", "start_time"],
                condition=Q(status="active"),
                name="booking_user_start_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.room}, {self.start_time:%Y-%m-%d %H:%M})"
