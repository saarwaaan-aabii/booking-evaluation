"""TODO 3 — Export a city catalogue summary as a JSON string."""
import json
from django.db.models import Sum
from rooms.models import Location, Room

def export_city_summary(city: str) -> str:
    """Return JSON containing city, total_rooms, total_capacity, room_codes."""
    if not isinstance(city, str) or not city.strip():
        raise ValueError('city must be a non-empty string')
    requested = city.strip()

    location = Location.objects.filter(city__iexact=requested).first()
    city_name = location.city if location else requested

    rooms = Room.objects.filter(location__city__iexact=requested)
    total_capacity = rooms.aggregate(total=Sum('capacity'))['total'] or 0
    room_codes = sorted(rooms.values_list('code', flat=True))

    return json.dumps({
        'city': city_name,
        'total_rooms': len(room_codes),
        'total_capacity': total_capacity,
        'room_codes': room_codes,
    })
