"""TODO 2 — Read-only rooms endpoint with an optional city filter."""
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rooms.models import Room
from rooms.serializers import RoomSerializer

class RoomListView(generics.ListAPIView):
    serializer_class = RoomSerializer
    queryset = Room.objects.select_related('location').order_by('code')

    def get_queryset(self):
        queryset = super().get_queryset()
        city = self.request.query_params.get('city')
        if city is None:
            return queryset
        city = city.strip()
        if not city:
            raise ValidationError({'city': 'This parameter cannot be blank.'})
        return queryset.filter(location__city__iexact=city)
