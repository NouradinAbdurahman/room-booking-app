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


MINE_ONLY_TRUE = "Use mine=true to list your own upcoming bookings."
MINE_NOT_MIXED = "Use either mine=true, or room and date, not both."


class BookingListFilter(serializers.Serializer):
    """The query of GET /api/bookings/, in exactly one of two forms (ADR 0006):
    `mine=true` (the session User's Upcoming bookings), or a Room and a Doha Day
    given as `room` and `date`. Validated data is {"mine": True} or {"room", "date"}.
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

    def to_internal_value(self, data):
        # The mine form is checked first, so mine=true&room=… reports the mixed
        # forms rather than whatever is wrong with the room.
        if "mine" in data:
            if data.get("mine") != "true":
                raise serializers.ValidationError({"mine": [MINE_ONLY_TRUE]})
            if "room" in data or "date" in data:
                raise serializers.ValidationError({"mine": [MINE_NOT_MIXED]})
            return {"mine": True}
        return super().to_internal_value(data)

    def validate(self, attrs):
        if attrs.get("mine"):
            return attrs
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
        # Check the instant itself: an offset with seconds (e.g. +03:00:30)
        # would otherwise turn a whole-minute wall clock into an odd instant.
        if value.second or value.microsecond or value.utcoffset().total_seconds() % 60:
            self.fail("not_whole_minute")
        return value


class CreateBookingSerializer(serializers.Serializer):
    """Step 1 of spec §5: only the request's shape. The rules live in bookings.services."""

    room_id = serializers.IntegerField(error_messages={"invalid": "Room must be a Room id."})
    title = serializers.CharField(max_length=200)
    start_time = OffsetDateTimeField()
    end_time = OffsetDateTimeField()
