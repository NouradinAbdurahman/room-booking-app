from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response

from . import services
from .doha_time import doha_day_bounds
from .models import Booking, BookingStatus
from .serializers import BookingListFilter, BookingSerializer, CreateBookingSerializer


class BookingListView(ListCreateAPIView):
    """GET: a Room's Day schedule (ADRs 0005, 0006). POST: book a Room (spec §5)."""

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

    def create(self, request, *args, **kwargs):
        shape = CreateBookingSerializer(data=request.data)
        shape.is_valid(raise_exception=True)
        # The Booker is always the session User, never a request field.
        booking = services.create_booking(booker=request.user, **shape.validated_data)
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)
