from rest_framework.generics import ListAPIView

from .models import Room
from .serializers import RoomSerializer


class RoomListView(ListAPIView):
    queryset = Room.objects.all()  # ordered by name (Room.Meta.ordering)
    serializer_class = RoomSerializer
