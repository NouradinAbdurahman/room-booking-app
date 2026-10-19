from rest_framework.generics import ListAPIView

from .doha_time import doha_day_bounds
from .models import Booking, BookingStatus
from .serializers import BookingListFilter, BookingSerializer


class BookingListView(ListAPIView):
    """A Room's Day schedule: every Active booking overlapping one Doha Day (ADRs 0005, 0006)."""

    serializer_class = BookingSerializer

    def get_queryset(self):
        query = BookingListFilter(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        day_start, day_end = doha_day_bounds(query.validated_data["date"])

        return (
            Booking.objects.filter(
                room=query.validated_data["room"],
                status=BookingStatus.ACTIVE,
                # Overlap, not "starts on": a Booking crossing midnight shows on both Days.
                start_time__lt=day_end,
                end_time__gt=day_start,
            )
            .select_related("room", "user")
            .order_by("start_time", "id")
        )
