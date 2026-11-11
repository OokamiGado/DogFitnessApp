from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.core.paginator import Paginator

from clients.models import Dog, AuditLog
from clients.audit import log_action
from plans.models import TrainingPlan
from .models import TrainingSession, Booking, PendingBookingRequest
from .forms import TrainingSessionForm, BookingForm, NewClientBookingForm, PublicBookingRequestForm, BookingJournalForm

# Maksymalna liczba zgloszen publicznych z jednego adresu IP w ciagu
# godziny - prosta ochrona antyspamowa (bez captchy, zgodnie z decyzja).
PUBLIC_REQUEST_RATE_LIMIT = 3
PUBLIC_REQUEST_RATE_LIMIT_MINUTES = 60


def get_client_ip(request):
    """Odczytuje prawdziwy adres IP klienta. Na hostingach za reverse
    proxy (np. Render) prawdziwy IP jest w nagłowku X-Forwarded-For
    (pierwszy adres na liscie), a request.META['REMOTE_ADDR'] wskazuje
    na adres proxy, nie klienta."""
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ============ TRAINING SESSION (Terminy) ============

SESSIONS_PER_PAGE = 20


@login_required
def session_list(request):
    """Agenda - lista nadchodzacych terminow (domyslnie), z mozliwoscia
    przejscia do widoku 'Wszystkie' (historia) przez filtr. Wyszukiwanie
    po tytule, miejscu ORAZ imieniu zapisanego psa."""
    show_all = request.GET.get('show') == 'all'
    sessions = TrainingSession.objects.exclude(status=TrainingSession.STATUS_CANCELLED)

    if not show_all:
        sessions = sessions.filter(date__gte=date.today())

    search_query = request.GET.get('q', '').strip()
    if search_query:
        sessions = sessions.filter(
            Q(title__icontains=search_query) | Q(location__icontains=search_query) |
            Q(bookings__dog__name__icontains=search_query)
        ).distinct()

    sessions = sessions.select_related().prefetch_related('bookings__dog')

    paginator = Paginator(sessions, SESSIONS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'scheduling/session_list.html', {
        'page_obj': page_obj,
        'show_all': show_all,
        'search_query': search_query,
        'today': date.today(),
    })


@login_required
def session_calendar(request):
    """Widok kalendarza (FullCalendar) - szablon renderuje JS, dane
    pobierane asynchronicznie z session_calendar_feed (JSON)."""
    return render(request, 'scheduling/session_calendar.html')


@login_required
def session_calendar_feed(request):
    """JSON feed zdarzen dla FullCalendar (parametry start/end przekazywane
    automatycznie przez FullCalendar przy zmianie widoku/miesiaca)."""
    start = request.GET.get('start', '')[:10]
    end = request.GET.get('end', '')[:10]

    sessions = TrainingSession.objects.exclude(status=TrainingSession.STATUS_CANCELLED)
    if start:
        sessions = sessions.filter(date__gte=start)
    if end:
        sessions = sessions.filter(date__lte=end)

    events = []
    for s in sessions:
        confirmed = s.confirmed_count()
        color = '#A4243B' if s.is_full() else ('#D4AF37' if confirmed > 0 else '#7FB069')
        events.append({
            'id': s.pk,
            'title': f"{s.title or 'Trening'} ({confirmed}/{s.capacity})",
            'start': f"{s.date.isoformat()}T{s.start_time.isoformat()}",
            'end': f"{s.date.isoformat()}T{s.end_time.isoformat()}",
            'url': f'/scheduling/sessions/{s.pk}/',
            'color': color,
        })
    return JsonResponse(events, safe=False)


@login_required
def session_create(request):
    if request.method == 'POST':
        form = TrainingSessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            log_action(request, AuditLog.ACTION_CREATED, AuditLog.TARGET_SESSION, session,
                       f'Utworzono termin "{session}"')
            conflicts = session.get_conflicting_sessions()
            if conflicts:
                conflict_desc = ', '.join(str(c) for c in conflicts)
                messages.warning(request, f'Uwaga: ten termin nakladasie z: {conflict_desc}. Zapisano mimo to.')
            messages.success(request, 'Termin zostal dodany.')
            return redirect('session_detail', pk=session.pk)
    else:
        form = TrainingSessionForm(initial={'date': request.GET.get('date', date.today())})
    return render(request, 'scheduling/session_form.html', {'form': form, 'title': 'Dodaj termin'})


@login_required
def session_update(request, pk):
    session = get_object_or_404(TrainingSession, pk=pk)
    if request.method == 'POST':
        form = TrainingSessionForm(request.POST, instance=session)
        if form.is_valid():
            changed_fields = list(form.changed_data)
            session = form.save()
            description = f'Zmieniono pola: {", ".join(changed_fields)}' if changed_fields else 'Zapisano (brak zmian danych)'
            log_action(request, AuditLog.ACTION_UPDATED, AuditLog.TARGET_SESSION, session, description)
            conflicts = session.get_conflicting_sessions()
            if conflicts:
                conflict_desc = ', '.join(str(c) for c in conflicts)
                messages.warning(request, f'Uwaga: ten termin naklada sie z: {conflict_desc}. Zapisano mimo to.')
            messages.success(request, 'Termin zostal zaktualizowany.')
            return redirect('session_detail', pk=session.pk)
    else:
        form = TrainingSessionForm(instance=session)
    return render(request, 'scheduling/session_form.html', {'form': form, 'title': 'Edytuj termin', 'session_obj': session})


@login_required
def session_detail(request, pk):
    session = get_object_or_404(TrainingSession, pk=pk)
    confirmed = session.confirmed_bookings().select_related('dog', 'dog__owner', 'linked_plan')
    waiting = session.waiting_list_bookings().select_related('dog', 'dog__owner', 'linked_plan')
    cancelled = session.bookings.filter(status=Booking.STATUS_CANCELLED).select_related('dog', 'dog__owner')
    completed = session.bookings.filter(
        status__in=[Booking.STATUS_ATTENDED, Booking.STATUS_NO_SHOW]
    ).select_related('dog', 'dog__owner', 'linked_plan')
    conflicts = session.get_conflicting_sessions()
    pending_requests = session.pending_requests.filter(status=PendingBookingRequest.STATUS_PENDING)

    return render(request, 'scheduling/session_detail.html', {
        'session_obj': session,
        'confirmed_bookings': confirmed,
        'waiting_bookings': waiting,
        'completed_bookings': completed,
        'cancelled_bookings': cancelled,
        'conflicts': conflicts,
        'pending_requests': pending_requests,
        'booking_statuses': Booking.STATUS_CHOICES,
    })


@login_required
def session_delete(request, pk):
    """'Usuniecie' terminu = odwolanie (kaskadowo odwoluje rezerwacje) -
    zachowujemy historie, nie usuwamy fizycznie z bazy."""
    session = get_object_or_404(TrainingSession, pk=pk)
    if request.method == 'POST':
        session.cancel()
        log_action(request, AuditLog.ACTION_CANCELLED, AuditLog.TARGET_SESSION, session,
                   f'Odwolano termin "{session}"')
        messages.success(request, 'Termin zostal odwolany.')
        return redirect('session_list')
    return render(request, 'scheduling/session_confirm_delete.html', {'session_obj': session})


@login_required
def session_duplicate(request, pk):
    """Powiela termin na kolejny tydzien (ta sama godzina/pojemnosc),
    bez kopiowania rezerwacji."""
    session = get_object_or_404(TrainingSession, pk=pk)
    if request.method == 'POST':
        new_session = session.duplicate_next_week()
        log_action(request, AuditLog.ACTION_DUPLICATED, AuditLog.TARGET_SESSION, new_session,
                   f'Powielono termin z "{session}" na "{new_session}"')
        messages.success(request, f'Utworzono nowy termin: {new_session}.')
        return redirect('session_detail', pk=new_session.pk)
    return render(request, 'scheduling/session_duplicate_confirm.html', {'session_obj': session})


# ============ BOOKING (Rezerwacje) ============

@login_required
def booking_add_existing(request, session_pk):
    """Zapisuje ISTNIEJACEGO psa na termin. Jesli termin jest pelny,
    rezerwacja automatycznie trafia na liste rezerwowa."""
    session = get_object_or_404(TrainingSession, pk=session_pk)
    if request.method == 'POST':
        form = BookingForm(request.POST, session=session)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.session = session
            booking.status = Booking.STATUS_WAITING_LIST if session.is_full() else Booking.STATUS_CONFIRMED
            booking.save()
            if booking.status == Booking.STATUS_WAITING_LIST:
                messages.warning(request, f'{booking.dog.name} dodany na liste rezerwowa (termin jest pelny).')
            else:
                messages.success(request, f'{booking.dog.name} zostal zapisany na termin.')
            return redirect('session_detail', pk=session.pk)
    else:
        form = BookingForm(session=session)
    return render(request, 'scheduling/booking_form.html', {
        'form': form, 'session_obj': session, 'mode': 'existing',
    })


@login_required
def booking_add_new_client(request, session_pk):
    """Zapisuje NOWEGO klienta (nieistniejacego w bazie) na termin -
    tworzy prawdziwy Owner+Dog, zeby reszta systemu dzialala identycznie
    jak dla istniejacych klientow. Jesli znaleziono istniejacego
    wlasciciela po numerze telefonu, NIE tworzy duplikatu."""
    session = get_object_or_404(TrainingSession, pk=session_pk)
    if request.method == 'POST':
        form = NewClientBookingForm(request.POST)
        if form.is_valid():
            existing_owner = form.find_existing_owner()
            dog = form.save_owner_and_dog(existing_owner=existing_owner)

            status = Booking.STATUS_WAITING_LIST if session.is_full() else Booking.STATUS_CONFIRMED
            Booking.objects.create(
                session=session, dog=dog, status=status,
                notes=form.cleaned_data.get('notes', ''),
            )
            if existing_owner:
                messages.info(request, f'Znaleziono istniejacego klienta "{existing_owner.full_name}" - podlinkowano (nie utworzono duplikatu).')
            if status == Booking.STATUS_WAITING_LIST:
                messages.warning(request, f'{dog.name} dodany na liste rezerwowa (termin jest pelny).')
            else:
                messages.success(request, f'{dog.name} zostal zapisany na termin.')
            return redirect('session_detail', pk=session.pk)
    else:
        form = NewClientBookingForm()
    return render(request, 'scheduling/booking_form.html', {
        'form': form, 'session_obj': session, 'mode': 'new',
    })


@login_required
def booking_set_status(request, pk, new_status):
    """Zmienia status rezerwacji (odwolaj / oznacz obecnosc / nieobecnosc
    / przywroc do 'zapisany'). Jesli rezerwacja przechodzi w 'cancelled'
    lub 'no_show', automatycznie probuje awansowac najdluzej czekajaca
    osobe z listy rezerwowej (FIFO).

    Gdy nowy status to 'attended' (obecny) - przekierowuje do formularza
    notatki z treningu (dziennik) - naturalny moment w przeplywie pracy.
    Notatka jest OPCJONALNA - formularz ma link 'Pomiń na razie'."""
    booking = get_object_or_404(Booking, pk=pk)
    valid_statuses = [choice[0] for choice in Booking.STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, 'Niepoprawny status.')
        return redirect('session_detail', pk=booking.session.pk)

    if request.method == 'POST':
        was_taking_slot = booking.status in (Booking.STATUS_CONFIRMED,)
        old_status_display = booking.get_status_display()
        booking.status = new_status
        booking.save()
        log_action(request, AuditLog.ACTION_STATUS_TOGGLED, AuditLog.TARGET_BOOKING, booking,
                   f'{booking.dog.name}: status zmieniony z "{old_status_display}" na "{booking.get_status_display()}"')

        if was_taking_slot and new_status in (Booking.STATUS_CANCELLED, Booking.STATUS_NO_SHOW):
            promoted = booking.promote_from_waiting_list_if_needed()
            if promoted:
                messages.info(request, f'{promoted.dog.name} zostal automatycznie przeniesiony z listy rezerwowej na wolne miejsce.')

        messages.success(request, f'Status rezerwacji zmieniony na "{booking.get_status_display()}".')

        if new_status == Booking.STATUS_ATTENDED:
            return redirect('booking_journal_edit', pk=booking.pk)

    return redirect('session_detail', pk=booking.session.pk)


@login_required
def booking_journal_edit(request, pk):
    """Formularz notatki z treningu (dziennik treningowy) dla konkretnej
    rezerwacji - dostepny w kazdym momencie (nie tylko po oznaczeniu
    'obecny'), np. z linku na karcie psa."""
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        form = BookingJournalForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notatka z treningu zostala zapisana.')
            return redirect('session_detail', pk=booking.session.pk)
    else:
        form = BookingJournalForm(instance=booking)
    return render(request, 'scheduling/booking_journal_form.html', {
        'form': form, 'booking': booking,
    })


@login_required
def booking_link_plan(request, pk):
    """Ustawia/usuwa powiazany plan treningowy dla rezerwacji (AJAX-like,
    ale dziala jako zwykly POST + redirect - prostota > SPA)."""
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        plan_pk = request.POST.get('plan')
        if plan_pk:
            plan = get_object_or_404(TrainingPlan, pk=plan_pk, dog=booking.dog)
            booking.linked_plan = plan
        else:
            booking.linked_plan = None
        booking.save()
        messages.success(request, 'Powiazany plan zaktualizowany.')
    return redirect('session_detail', pk=booking.session.pk)


# ============ AJAX HELPERS ============

@login_required
def ajax_dog_plans(request, dog_pk):
    """Zwraca liste planow treningowych danego psa (JSON) - uzywane do
    dynamicznego wypelnienia pola 'linked_plan' w formularzu rezerwacji
    po wybraniu psa (bez przeladowania strony)."""
    dog = get_object_or_404(Dog, pk=dog_pk)
    plans = TrainingPlan.objects.filter(dog=dog, is_active=True).values('pk', 'name')
    return JsonResponse({'plans': list(plans)})



# ============ PUBLICZNY FORMULARZ ZAPISOW (Etap 4) ============
# Widoki NIEZALOGOWANE (bez @login_required) - dostepne dla gosci.
# Reszta modulu zostaje w pelni chroniona jak dotychczas.

def public_session_list(request):
    """Publiczna strona 'Zobacz dostepne terminy' - lista wszystkich
    terminow is_public=True, status='scheduled', data w przyszlosci.
    Pokazuje tylko liczbe wolnych miejsc, NIGDY nazwisk zapisanych osob.
    Filtr zakresu dat: 7 dni / 30 dni / wszystkie (domyslnie 30 dni)."""
    range_filter = request.GET.get('range', '30')

    sessions = TrainingSession.objects.filter(
        is_public=True, status=TrainingSession.STATUS_SCHEDULED, date__gte=date.today(),
    ).order_by('date', 'start_time')

    if range_filter == '7':
        sessions = sessions.filter(date__lte=date.today() + timedelta(days=7))
    elif range_filter == '30':
        sessions = sessions.filter(date__lte=date.today() + timedelta(days=30))
    # range_filter == 'all' -> brak dodatkowego filtra

    return render(request, 'scheduling/public_session_list.html', {
        'sessions': sessions,
        'range_filter': range_filter,
    })


def public_booking_request(request, pk):
    """Formularz PUBLICZNY zgloszenia checi zapisu na konkretny termin.
    NIE tworzy Owner/Dog/Booking - zapisuje PendingBookingRequest do
    recznej weryfikacji przez trenera. Chroniony honeypotem + limitem
    zgloszen z IP + blokada duplikatu (ten sam telefon + ten sam termin)."""
    session = get_object_or_404(TrainingSession, pk=pk)
    if not session.is_publicly_bookable():
        raise Http404("Ten termin nie jest juz dostepny.")

    client_ip = get_client_ip(request)

    if request.method == 'POST':
        form = PublicBookingRequestForm(request.POST)

        if form.is_valid():
            if form.is_spam():
                # Honeypot wypelniony - udajemy sukces (nie zdradzamy
                # botowi ze zostal wykryty), ALE nic nie zapisujemy.
                return redirect('public_booking_thank_you')

            recent_count = PendingBookingRequest.count_recent_from_ip(
                client_ip, minutes=PUBLIC_REQUEST_RATE_LIMIT_MINUTES
            )
            if recent_count >= PUBLIC_REQUEST_RATE_LIMIT:
                form.add_error(None, 'Zbyt wiele zgloszen z tego adresu. Sprobuj pozniej.')
            elif PendingBookingRequest.has_pending_duplicate(session, form.cleaned_data['submitted_phone']):
                form.add_error(None, 'Juz wyslano zgloszenie na ten termin z tego numeru telefonu. Czekaj na kontakt trenera.')
            else:
                PendingBookingRequest.objects.create(
                    session=session,
                    submitted_name=form.cleaned_data['submitted_name'],
                    submitted_phone=form.cleaned_data['submitted_phone'],
                    submitted_email=form.cleaned_data.get('submitted_email', ''),
                    dog_name=form.cleaned_data['dog_name'],
                    message=form.cleaned_data.get('message', ''),
                    rodo_consent=form.cleaned_data['rodo_consent'],
                    ip_address=client_ip,
                )
                return redirect('public_booking_thank_you')
    else:
        form = PublicBookingRequestForm()

    return render(request, 'scheduling/public_booking_form.html', {
        'form': form, 'session_obj': session,
    })


def public_booking_thank_you(request):
    """Strona potwierdzenia po zlozeniu zgloszenia (lub po 'cichym'
    odrzuceniu spamu przez honeypot - identyczna strona w obu przypadkach,
    zeby nie zdradzac botom mechanizmu wykrywania)."""
    return render(request, 'scheduling/public_booking_thank_you.html')


# ============ MODERACJA WNIOSKOW (Etap 4) ============

@login_required
def pending_request_list(request):
    """Kolejka wnioskow od gosci czekajacych na weryfikacje trenera."""
    pending = PendingBookingRequest.objects.filter(
        status=PendingBookingRequest.STATUS_PENDING
    ).select_related('session').order_by('created_at')
    decided = PendingBookingRequest.objects.exclude(
        status=PendingBookingRequest.STATUS_PENDING
    ).select_related('session', 'decided_by').order_by('-decided_at')[:20]

    return render(request, 'scheduling/pending_request_list.html', {
        'pending_requests': pending,
        'decided_requests': decided,
    })


@login_required
def pending_request_approve(request, pk):
    """Zatwierdza wniosek goscia - tworzy (lub podlacza istniejacego)
    Owner+Dog+Booking. Jesli termin okazal sie pelny w miedzyczasie,
    rezerwacja trafia na liste rezerwowa (z jasnym komunikatem)."""
    pending_request = get_object_or_404(PendingBookingRequest, pk=pk)
    if request.method == 'POST':
        try:
            result = pending_request.approve(user=request.user)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('pending_request_list')

        log_action(request, AuditLog.ACTION_APPROVED, AuditLog.TARGET_PENDING_REQUEST, pending_request,
                   f'Zatwierdzono wniosek {pending_request.submitted_name} - pies {result["dog"].name}')

        if result['matched_existing_owner']:
            messages.info(request, f'Znaleziono istniejacego klienta "{result["owner"].full_name}" - podlinkowano (nie utworzono duplikatu).')
        if result['went_to_waiting_list']:
            messages.warning(request, f'Termin byl juz pelny - {result["dog"].name} zostal dodany na LISTE REZERWOWA.')
        else:
            messages.success(request, f'Wniosek zatwierdzony - {result["dog"].name} zostal zapisany na termin.')
    return redirect('pending_request_list')


@login_required
def pending_request_reject(request, pk):
    """Odrzuca wniosek goscia - zero sladu w Owner/Dog/Booking."""
    pending_request = get_object_or_404(PendingBookingRequest, pk=pk)
    if request.method == 'POST':
        note = request.POST.get('rejection_note', '')
        try:
            pending_request.reject(user=request.user, note=note)
            log_action(request, AuditLog.ACTION_REJECTED, AuditLog.TARGET_PENDING_REQUEST, pending_request,
                       f'Odrzucono wniosek {pending_request.submitted_name}' + (f' - powod: {note}' if note else ''))
            messages.success(request, 'Wniosek zostal odrzucony.')
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('pending_request_list')
