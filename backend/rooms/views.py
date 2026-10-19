from rest_framework.generics import ListAPIView

from .models import Room
from .serializers import RoomSerializer


class RoomListView(ListAPIView):
    queryset = Room.objects.order_by("name")
    serializer_class = RoomSerializer
