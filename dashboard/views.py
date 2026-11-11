from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from clients.models import Owner
from scheduling.models import TrainingSession, PendingBookingRequest
from finance.models import Payment

UPCOMING_DAYS_RANGE = 7
RECENT_OWNERS_LIMIT = 5
UPCOMING_SESSIONS_LIMIT = 8
PENDING_REQUESTS_LIMIT = 5
PENDING_PAYMENTS_LIMIT = 5


@login_required
def dashboard_home(request):
    """Panel glowny (akcyjny) - zastepuje ekran powitalny po zalogowaniu.
    Pokazuje TYLKO to, co wymaga uwagi/akcji TERAZ - bez statystyk/
    wskaznikow (decyzja produktowa: czysto akcyjny widok)."""
    today = date.today()

    upcoming_sessions = TrainingSession.objects.filter(
        date__gte=today, date__lte=today + timedelta(days=UPCOMING_DAYS_RANGE),
        status=TrainingSession.STATUS_SCHEDULED,
    ).order_by('date', 'start_time').prefetch_related('bookings')[:UPCOMING_SESSIONS_LIMIT]

    pending_requests = PendingBookingRequest.objects.filter(
        status=PendingBookingRequest.STATUS_PENDING,
    ).select_related('session').order_by('created_at')[:PENDING_REQUESTS_LIMIT]
    pending_requests_total = PendingBookingRequest.objects.filter(
        status=PendingBookingRequest.STATUS_PENDING,
    ).count()

    recent_owners = Owner.objects.filter(is_active=True).order_by('-created_at')[:RECENT_OWNERS_LIMIT]

    pending_payments = []
    pending_payments_total_count = 0
    pending_payments_total_amount = Decimal('0')
    if request.user.is_staff:
        pending_payments = Payment.objects.filter(
            status=Payment.STATUS_PENDING,
        ).select_related('owner').order_by('payment_date')[:PENDING_PAYMENTS_LIMIT]
        pending_payments_total_count = Payment.objects.filter(status=Payment.STATUS_PENDING).count()
        pending_payments_total_amount = Payment.objects.filter(status=Payment.STATUS_PENDING).aggregate(
            total=Sum('amount'))['total'] or Decimal('0')

    return render(request, 'dashboard/home.html', {
        'today': today,
        'upcoming_sessions': upcoming_sessions,
        'pending_requests': pending_requests,
        'pending_requests_total': pending_requests_total,
        'recent_owners': recent_owners,
        'pending_payments': pending_payments,
        'pending_payments_total_count': pending_payments_total_count,
        'pending_payments_total_amount': pending_payments_total_amount,
    })
