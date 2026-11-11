import csv
from datetime import date
from decimal import Decimal
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.http import HttpResponse

from clients.models import Owner, AuditLog
from clients.audit import log_action
from .models import PricingPlan, Payment
from .forms import PricingPlanForm, PaymentForm

PAYMENTS_PER_PAGE = 25

MONTH_NAMES_PL = [
    '', 'Styczen', 'Luty', 'Marzec', 'Kwiecien', 'Maj', 'Czerwiec',
    'Lipiec', 'Sierpien', 'Wrzesien', 'Pazdziernik', 'Listopad', 'Grudzien',
]


def staff_required(view_func):
    """Modul Finanse zawiera dane podatkowo-wrazliwe (przychody, metody
    platnosci) - dostepny TYLKO dla uzytkownikow is_staff=True (tak jak
    Dziennik zmian i Wyglad dokumentow). Inaczej niz tamte dwa widoki
    (ktore tylko chowaja link w nawigacji, ale nie blokuja URL),
    tutaj blokujemy rowniez na poziomie widoku - defense in depth,
    bo to dane finansowe, nie estetyczne."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Brak uprawnien do modulu Finanse.')
            return redirect('dashboard_home')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_selected_year(request):
    """Bezpiecznie odczytuje rok z parametru GET 'year'. Jesli parametr
    jest niepoprawny (np. ?year=abc - literowka, stary link, reczna
    edycja URL) - zwraca biezacy rok zamiast rzucac ValueError (co
    wczesniej powodowalo blad 500)."""
    year_param = request.GET.get('year', '').strip()
    if year_param.isdigit() and len(year_param) == 4:
        return int(year_param)
    return date.today().year


# ============ CENNIK (PricingPlan) ============

@staff_required
def pricing_plan_list(request):
    plans = PricingPlan.objects.all()
    return render(request, 'finance/pricing_plan_list.html', {'plans': plans})


@staff_required
def pricing_plan_create(request):
    if request.method == 'POST':
        form = PricingPlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            log_action(request, AuditLog.ACTION_CREATED, AuditLog.TARGET_PRICING_PLAN, plan,
                       f'Utworzono pozycje cennika "{plan.name}" ({plan.price} PLN)')
            messages.success(request, f'Pozycja cennika "{plan.name}" zostala dodana.')
            return redirect('pricing_plan_list')
    else:
        form = PricingPlanForm()
    return render(request, 'finance/pricing_plan_form.html', {'form': form, 'title': 'Nowa pozycja cennika'})


@staff_required
def pricing_plan_update(request, pk):
    plan = get_object_or_404(PricingPlan, pk=pk)
    if request.method == 'POST':
        form = PricingPlanForm(request.POST, instance=plan)
        if form.is_valid():
            changed_fields = list(form.changed_data)
            form.save()
            description = f'Zmieniono pola: {", ".join(changed_fields)}' if changed_fields else 'Zapisano (brak zmian danych)'
            log_action(request, AuditLog.ACTION_UPDATED, AuditLog.TARGET_PRICING_PLAN, plan, description)
            messages.success(request, 'Pozycja cennika zostala zaktualizowana.')
            return redirect('pricing_plan_list')
    else:
        form = PricingPlanForm(instance=plan)
    return render(request, 'finance/pricing_plan_form.html', {'form': form, 'plan': plan, 'title': 'Edytuj pozycje cennika'})


@staff_required
def pricing_plan_delete(request, pk):
    """Usuniecie pozycji cennika - strona potwierdzenia (GET) + faktyczne
    usuniecie (POST), zapisane w dzienniku zmian. Platnosci historyczne
    powiazane z ta pozycja NIE zostana usuniete (FK na_delete=SET_NULL)."""
    plan = get_object_or_404(PricingPlan, pk=pk)
    if request.method == 'POST':
        plan_name = plan.name
        plan_price = plan.price
        log_action(request, AuditLog.ACTION_DELETED_PERMANENT, AuditLog.TARGET_PRICING_PLAN, plan,
                   f'Usunieto pozycje cennika "{plan_name}" ({plan_price} PLN)')
        plan.delete()
        messages.success(request, 'Pozycja cennika zostala usunieta.')
        return redirect('pricing_plan_list')
    return render(request, 'finance/pricing_plan_confirm_delete.html', {'plan': plan})


@staff_required
def pricing_plan_toggle_active(request, pk):
    plan = get_object_or_404(PricingPlan, pk=pk)
    if request.method == 'POST':
        plan.is_active = not plan.is_active
        plan.save()
        log_action(request, AuditLog.ACTION_STATUS_TOGGLED, AuditLog.TARGET_PRICING_PLAN, plan,
                   f'Zmieniono status pozycji cennika "{plan.name}" na: {"aktywna" if plan.is_active else "nieaktywna"}')
    return redirect('pricing_plan_list')


# ============ PLATNOSCI (Payment) ============

@staff_required
def payment_list(request):
    payments = Payment.objects.select_related('owner', 'booking__session', 'pricing_plan')

    owner_id = request.GET.get('owner', '').strip()
    if owner_id:
        payments = payments.filter(owner_id=owner_id)

    status_filter = request.GET.get('status', '').strip()
    if status_filter in (Payment.STATUS_PAID, Payment.STATUS_PENDING):
        payments = payments.filter(status=status_filter)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        payments = payments.filter(
            Q(owner__first_name__icontains=search_query) |
            Q(owner__last_name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(payments, PAYMENTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    pending_total = Payment.objects.filter(status=Payment.STATUS_PENDING).aggregate(
        total=Sum('amount'))['total'] or Decimal('0')
    pending_count = Payment.objects.filter(status=Payment.STATUS_PENDING).count()

    return render(request, 'finance/payment_list.html', {
        'page_obj': page_obj,
        'owner_id': owner_id,
        'status_filter': status_filter,
        'search_query': search_query,
        'pending_total': pending_total,
        'pending_count': pending_count,
    })


@staff_required
def payment_create(request, owner_pk=None, booking_pk=None):
    from scheduling.models import Booking
    fixed_owner = get_object_or_404(Owner, pk=owner_pk) if owner_pk else None
    fixed_booking = get_object_or_404(Booking, pk=booking_pk) if booking_pk else None

    if request.method == 'POST':
        form = PaymentForm(request.POST, fixed_owner=fixed_owner, fixed_booking=fixed_booking)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.save()
            log_action(request, AuditLog.ACTION_CREATED, AuditLog.TARGET_PAYMENT, payment,
                       f'Zarejestrowano platnosc {payment.amount} PLN od {payment.owner.full_name} '
                       f'({payment.get_status_display()}, {payment.get_method_display()})')
            messages.success(request, f'Platnosc {payment.amount} PLN zostala zarejestrowana.')
            if fixed_owner:
                return redirect('owner_detail', pk=fixed_owner.pk)
            if fixed_booking:
                return redirect('session_detail', pk=fixed_booking.session.pk)
            return redirect('payment_list')
    else:
        initial = {'payment_date': date.today()}
        form = PaymentForm(initial=initial, fixed_owner=fixed_owner, fixed_booking=fixed_booking)

    return render(request, 'finance/payment_form.html', {
        'form': form, 'title': 'Zarejestruj platnosc',
        'fixed_owner': fixed_owner, 'fixed_booking': fixed_booking,
    })


@staff_required
def payment_update(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            changed_fields = list(form.changed_data)
            form.save()
            description = f'Zmieniono pola: {", ".join(changed_fields)}' if changed_fields else 'Zapisano (brak zmian danych)'
            log_action(request, AuditLog.ACTION_UPDATED, AuditLog.TARGET_PAYMENT, payment, description)
            messages.success(request, 'Platnosc zostala zaktualizowana.')
            return redirect('payment_list')
    else:
        form = PaymentForm(instance=payment)
    return render(request, 'finance/payment_form.html', {'form': form, 'payment': payment, 'title': 'Edytuj platnosc'})


@staff_required
def payment_delete(request, pk):
    """Usuniecie platnosci - strona potwierdzenia (GET) + faktyczne
    usuniecie (POST). WAZNE: tworzymy wpis w dzienniku zmian PRZED
    usunieciem rekordu - to jedyny trwaly slad tej platnosci po usunieciu
    (opis zawiera kwote, klienta i date - wystarczajace do rekonstrukcji
    w razie potrzeby audytu)."""
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        log_action(request, AuditLog.ACTION_DELETED_PERMANENT, AuditLog.TARGET_PAYMENT, payment,
                   f'Usunieto platnosc {payment.amount} PLN od {payment.owner.full_name} '
                   f'z dnia {payment.payment_date.strftime("%d.%m.%Y")} ({payment.get_status_display()})')
        payment.delete()
        messages.success(request, 'Platnosc zostala usunieta.')
        return redirect('payment_list')
    return render(request, 'finance/payment_confirm_delete.html', {'payment': payment})


@staff_required
def payment_mark_paid(request, pk):
    """Szybkie oznaczenie oczekujacej platnosci jako oplaconej (np. z
    dashboardu lub z listy) - bez przechodzenia przez caly formularz."""
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        payment.status = Payment.STATUS_PAID
        if not payment.payment_date or payment.payment_date > date.today():
            payment.payment_date = date.today()
        payment.save()
        log_action(request, AuditLog.ACTION_STATUS_TOGGLED, AuditLog.TARGET_PAYMENT, payment,
                   f'Oznaczono platnosc {payment.amount} PLN od {payment.owner.full_name} jako oplacona')
        messages.success(request, f'Platnosc {payment.amount} PLN oznaczona jako oplacona.')

    referer = request.META.get('HTTP_REFERER', '')
    if referer and referer.startswith(request.build_absolute_uri('/')):
        return redirect(referer)
    return redirect('payment_list')


# ============ ZESTAWIENIA (raporty do celow podatkowych) ============

@staff_required
def finance_report(request):
    """Zestawienie przychodow - miesiac/kwartal/rok - do szybkiej
    weryfikacji wlasnej lub przekazania ksiegowej. Pokazuje TYLKO
    platnosci ze statusem 'oplacone' (STATUS_PAID) - oczekujace nie
    wliczaja sie do przychodu."""
    available_years = list(
        Payment.objects.filter(status=Payment.STATUS_PAID)
        .dates('payment_date', 'year')
    )
    available_years = sorted({d.year for d in available_years}, reverse=True)
    if not available_years:
        available_years = [date.today().year]

    selected_year = get_selected_year(request)
    if selected_year not in available_years:
        available_years.append(selected_year)
        available_years.sort(reverse=True)

    paid_qs = Payment.objects.filter(status=Payment.STATUS_PAID, payment_date__year=selected_year)

    monthly_data = []
    for month_num in range(1, 13):
        month_qs = paid_qs.filter(payment_date__month=month_num)
        agg = month_qs.aggregate(total=Sum('amount'), count=Count('id'))
        monthly_data.append({
            'month_num': month_num,
            'month_name': MONTH_NAMES_PL[month_num],
            'total': agg['total'] or Decimal('0'),
            'count': agg['count'] or 0,
        })

    quarterly_data = []
    for q_num in range(1, 5):
        months_in_q = monthly_data[(q_num - 1) * 3: q_num * 3]
        quarterly_data.append({
            'quarter_num': q_num,
            'total': sum(m['total'] for m in months_in_q),
            'count': sum(m['count'] for m in months_in_q),
        })

    year_total = paid_qs.aggregate(total=Sum('amount'), count=Count('id'))
    year_total_amount = year_total['total'] or Decimal('0')
    year_total_count = year_total['count'] or 0

    by_method = paid_qs.values('method').annotate(total=Sum('amount'), count=Count('id')).order_by('-total')
    method_labels = dict(Payment.METHOD_CHOICES)
    by_method_display = [
        {'method_label': method_labels.get(row['method'], row['method']), 'total': row['total'], 'count': row['count']}
        for row in by_method
    ]

    pending_in_year = Payment.objects.filter(
        status=Payment.STATUS_PENDING, payment_date__year=selected_year
    ).aggregate(total=Sum('amount'), count=Count('id'))
    pending_in_year_amount = pending_in_year['total'] or Decimal('0')
    pending_in_year_count = pending_in_year['count'] or 0

    return render(request, 'finance/finance_report.html', {
        'available_years': available_years,
        'selected_year': selected_year,
        'monthly_data': monthly_data,
        'quarterly_data': quarterly_data,
        'year_total_amount': year_total_amount,
        'year_total_count': year_total_count,
        'by_method_display': by_method_display,
        'pending_in_year_amount': pending_in_year_amount,
        'pending_in_year_count': pending_in_year_count,
    })


@staff_required
def finance_report_export_csv(request):
    """Eksport SZCZEGOLOWEJ listy oplaconych platnosci za wybrany rok -
    gotowe do przekazania ksiegowej / wlasnej weryfikacji podatkowej."""
    selected_year = get_selected_year(request)
    payments = Payment.objects.filter(
        status=Payment.STATUS_PAID, payment_date__year=selected_year
    ).select_related('owner').order_by('payment_date', 'id')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="przychody_{selected_year}.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Data', 'Klient', 'Kwota (PLN)', 'Metoda platnosci', 'Opis', 'Notatki'])

    method_labels = dict(Payment.METHOD_CHOICES)
    total = Decimal('0')
    for p in payments:
        writer.writerow([
            p.payment_date.strftime('%d.%m.%Y'), p.owner.full_name, str(p.amount).replace('.', ','),
            method_labels.get(p.method, p.method), p.description, p.notes,
        ])
        total += p.amount

    writer.writerow([])
    writer.writerow(['', 'SUMA ROCZNA:', str(total).replace('.', ','), '', '', ''])
    return response
