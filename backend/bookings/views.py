from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .doha_time import doha_day_bounds
from .models import Booking, BookingStatus
from .serializers import BookingListFilter, BookingSerializer, CreateBookingSerializer


class BookingListView(ListCreateAPIView):
    """GET: the session User's Upcoming bookings (mine=true), or a Room's Day
    schedule (room and date), ADRs 0005, 0006. POST: book a Room (spec §5)."""

    serializer_class = BookingSerializer

    def get_queryset(self):
        query = BookingListFilter(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        filters = query.validated_data

        if filters.get("mine"):
            # Upcoming: Active and not yet ended. The User comes from the session only.
            matching = {"user": self.request.user, "end_time__gt": services.current_time()}
        else:
            day_start, day_end = doha_day_bounds(filters["date"])
            # Overlap, not "starts on": a Booking crossing midnight shows on both Days.
            matching = {"room": filters["room"], "start_time__lt": day_end, "end_time__gt": day_start}

        return (
            Booking.objects.filter(status=BookingStatus.ACTIVE, **matching)
            .select_related("room", "user")
            .order_by("start_time", "id")
        )

    def create(self, request, *args, **kwargs):
        shape = CreateBookingSerializer(data=request.data)
        shape.is_valid(raise_exception=True)
        # The Booker is always the session User, never a request field.
        booking = services.create_booking(booker=request.user, **shape.validated_data)
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    """DELETE cancels (ADR 0002). There is no edit: cancel and book again."""

    def delete(self, request, pk):
        services.cancel_booking(booker=request.user, booking_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
