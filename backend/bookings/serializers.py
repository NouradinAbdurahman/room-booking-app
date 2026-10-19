from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from rooms.models import Room
from rooms.serializers import RoomSerializer

from .models import Booking

DATE_INVALID = "Date must be a real date written as YYYY-MM-DD."
DAY_FILTER_REQUIRED = "Required, together with {other}, to show a Room's Day schedule."


class BookerSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "username"]


class BookingSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)
    # The model's `user` is the Booker; the API calls it booked_by (ADR 0006).
    booked_by = BookerSerializer(source="user", read_only=True)

    class Meta:
        model = Booking
        fields = ["id", "room", "title", "start_time", "end_time", "booked_by", "created_at"]


class BookingListFilter(serializers.Serializer):
    """The query of GET /api/bookings/: a Room and a Doha Day, given as `date` (ADR 0006).

    `mine=true` is the other filter form; it arrives with My Bookings (ticket 11).
    """

    room = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "No Room has this id.",
            "incorrect_type": "Room must be a Room id.",
        },
    )
    date = serializers.DateField(
        input_formats=["%Y-%m-%d"],
        required=False,
        error_messages={"invalid": DATE_INVALID},
    )

    def validate_date(self, value):
        # The parser also accepts "2026-1-5". The API takes exactly YYYY-MM-DD:
        # the parsed date must write back as the very string that was sent.
        if value.isoformat() != self.initial_data.get("date"):
            raise serializers.ValidationError(DATE_INVALID)
        return value

    def validate(self, attrs):
        if "mine" in self.initial_data:
            raise serializers.ValidationError({"mine": ["Listing your own bookings is not available yet."]})
        missing = {}
        if "room" not in attrs:
            missing["room"] = [DAY_FILTER_REQUIRED.format(other="date")]
        if "date" not in attrs:
            missing["date"] = [DAY_FILTER_REQUIRED.format(other="room")]
        if missing:
            raise serializers.ValidationError(missing)
        return attrs


class OffsetDateTimeField(serializers.Field):
    """An ISO-8601 time that carries a UTC offset and is a whole minute (ADR 0005).

    DRF's own DateTimeField would quietly read a time without an offset as
    server-local time; here "10:00" alone is refused as ambiguous.
    """

    default_error_messages = {
        "invalid": "Use an ISO-8601 time such as 2026-10-20T10:00:00+03:00.",
        "no_offset": "Include a UTC offset, for example +03:00.",
        "not_whole_minute": "Use whole minutes; seconds must be zero.",
    }

    def to_internal_value(self, data):
        try:
            value = parse_datetime(data) if isinstance(data, str) else None
        except ValueError:  # well-formed but impossible, e.g. month 13
            value = None
        if value is None:
            self.fail("invalid")
        if value.tzinfo is None:
            self.fail("no_offset")
        if value.second or value.microsecond:
            self.fail("not_whole_minute")
        return value


class CreateBookingSerializer(serializers.Serializer):
    """Step 1 of spec §5: only the request's shape. The rules live in bookings.services."""

    room_id = serializers.IntegerField(error_messages={"invalid": "Room must be a Room id."})
    title = serializers.CharField(max_length=200)
    start_time = OffsetDateTimeField()
    end_time = OffsetDateTimeField()
