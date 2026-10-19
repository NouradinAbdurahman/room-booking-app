from django.contrib.auth import get_user_model
from rest_framework import serializers

from rooms.models import Room
from rooms.serializers import RoomSerializer

from .models import Booking

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
    """The query of GET /api/bookings/: a Room and a Doha date (ADR 0006).

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
        error_messages={"invalid": "Date must be a real date written as YYYY-MM-DD."},
    )

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
