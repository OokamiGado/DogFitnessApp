"""
scheduling/context_processors.py

Context processor dodajacy licznik oczekujacych wnioskow o rezerwacje
(PendingBookingRequest ze status='pending') do KAZDEGO renderowanego
widoku - uzywane w base.html do pokazania badge'a w nawigacji
(np. "Wnioski (2)"), bez koniecznosci dopisywania tego w kazdym widoku.
"""

from .models import PendingBookingRequest


def pending_requests_count(request):
    if not request.user.is_authenticated:
        return {}
    count = PendingBookingRequest.objects.filter(status=PendingBookingRequest.STATUS_PENDING).count()
    return {'pending_requests_count': count}
