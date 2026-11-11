import csv
import os
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse

from .models import Owner, Dog, AuditLog
from .forms import OwnerForm, DogForm
from .audit import log_action

CLIENTS_PER_PAGE = 25

PHONE_WARNING_MSG = 'Numer telefonu moze byc niepoprawny - sprawdz, czy to nie pomylka. Zapisano mimo to.'


def _duplicate_phone_warning(owner_obj):
    return f'Uwaga: ten numer telefonu jest juz przypisany do klienta "{owner_obj.full_name}". Zapisano mimo to.'


# ============ OWNER ============

@login_required
def owner_list(request):
    owners = Owner.objects.filter(is_active=True).prefetch_related('dogs')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        owners = owners.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(dogs__name__icontains=search_query)
        ).distinct()

    rodo_filter = request.GET.get('rodo', '').strip()
    if rodo_filter == 'yes':
        owners = owners.filter(rodo_consent=True)
    elif rodo_filter == 'no':
        owners = owners.filter(rodo_consent=False)

    paginator = Paginator(owners, CLIENTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    stats = {
        'owners_count': Owner.objects.filter(is_active=True).count(),
        'dogs_count': Dog.objects.filter(is_active=True).count(),
        'paused_dogs_count': Dog.objects.filter(is_active=True, training_status=Dog.STATUS_PAUSED).count(),
        'owners_without_rodo': Owner.objects.filter(is_active=True, rodo_consent=False).count(),
    }

    return render(request, 'clients/owner_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'rodo_filter': rodo_filter,
        'stats': stats,
    })


@login_required
def owner_create(request):
    if request.method == 'POST':
        form = OwnerForm(request.POST)
        if form.is_valid():
            duplicate_owner = form.is_phone_duplicate()
            owner = form.save()
            if form.is_phone_suspicious():
                messages.warning(request, PHONE_WARNING_MSG)
            if duplicate_owner:
                messages.warning(request, _duplicate_phone_warning(duplicate_owner))
            log_action(request, AuditLog.ACTION_CREATED, AuditLog.TARGET_OWNER, owner,
                       f'Dodano klienta {owner.full_name}')
            messages.success(request, 'Wlasciciel zostal dodany.')
            return redirect('owner_detail', pk=owner.pk)
    else:
        form = OwnerForm()
    return render(request, 'clients/owner_form.html', {
        'form': form,
        'title': 'Dodaj klienta',
    })


@login_required
def owner_update(request, pk):
    owner = get_object_or_404(Owner, pk=pk)
    if owner.is_anonymized:
        messages.error(request, 'Ten klient zostal zanonimizowany - edycja danych osobowych nie jest mozliwa.')
        return redirect('owner_archived_list')
    if request.method == 'POST':
        form = OwnerForm(request.POST, instance=owner)
        if form.is_valid():
            duplicate_owner = form.is_phone_duplicate()
            changed_fields = list(form.changed_data)
            form.save()
            if form.is_phone_suspicious():
                messages.warning(request, PHONE_WARNING_MSG)
            if duplicate_owner:
                messages.warning(request, _duplicate_phone_warning(duplicate_owner))
            description = f'Zmieniono pola: {", ".join(changed_fields)}' if changed_fields else 'Zapisano (brak zmian danych)'
            log_action(request, AuditLog.ACTION_UPDATED, AuditLog.TARGET_OWNER, owner, description)
            messages.success(request, 'Dane wlasciciela zostaly zaktualizowane.')
            return redirect('owner_detail', pk=owner.pk)
    else:
        form = OwnerForm(instance=owner)
    return render(request, 'clients/owner_form.html', {
        'form': form,
        'title': 'Edytuj klienta',
        'owner': owner,
    })


@login_required
def owner_detail(request, pk):
    owner = get_object_or_404(Owner, pk=pk)
    return render(request, 'clients/owner_detail.html', {
        'owner': owner,
        'dogs': owner.dogs.filter(is_active=True),
    })


@login_required
def owner_delete(request, pk):
    owner = get_object_or_404(Owner, pk=pk)
    active_dogs_count = owner.dogs.filter(is_active=True).count()
    if request.method == 'POST':
        owner.is_active = False
        owner.save()
        log_action(request, AuditLog.ACTION_ARCHIVED, AuditLog.TARGET_OWNER, owner,
                   f'Zarchiwizowano klienta {owner.full_name}')
        messages.success(request, 'Klient zostal przeniesiony do archiwum.')
        return redirect('owner_list')
    return render(request, 'clients/owner_confirm_delete.html', {
        'owner': owner,
        'active_dogs_count': active_dogs_count,
    })


@login_required
def owner_archived_list(request):
    owners = Owner.objects.filter(is_active=False).order_by('-updated_at')
    return render(request, 'clients/owner_archived_list.html', {'owners': owners})


@login_required
def owner_restore(request, pk):
    owner = get_object_or_404(Owner, pk=pk, is_active=False)
    if request.method == 'POST':
        owner.is_active = True
        owner.save()
        log_action(request, AuditLog.ACTION_RESTORED, AuditLog.TARGET_OWNER, owner,
                   f'Przywrocono klienta {owner.full_name}')
        messages.success(request, 'Klient zostal przywrocony.')
    return redirect('owner_archived_list')


@login_required
def owner_anonymize(request, pk):
    """Anonimizuje dane osobowe klienta (RODO) - NIE usuwa psow, planow
    treningowych, rezerwacji ani dziennika treningowego. Dostepne tylko
    dla zarchiwizowanych klientow (is_active=False), analogicznie do
    usuniecia na zawsze - ale bez utraty historii merytorycznej."""
    owner = get_object_or_404(Owner, pk=pk, is_active=False)
    if owner.is_anonymized:
        messages.info(request, 'Ten klient jest juz zanonimizowany.')
        return redirect('owner_archived_list')
    if request.method == 'POST':
        original_name = owner.full_name
        owner.anonymize()
        log_action(request, AuditLog.ACTION_ANONYMIZED, AuditLog.TARGET_OWNER, owner,
                   f'Zanonimizowano dane osobowe klienta (byl: {original_name}) - psy i plany treningowe zachowane')
        messages.success(request, 'Dane osobowe klienta zostaly zanonimizowane. Psy i plany treningowe zostaly zachowane.')
    return redirect('owner_archived_list')


@login_required
def owner_delete_permanent(request, pk):
    owner = get_object_or_404(Owner, pk=pk, is_active=False)
    if request.method == 'POST':
        log_action(request, AuditLog.ACTION_DELETED_PERMANENT, AuditLog.TARGET_OWNER, owner,
                   f'Usunieto na zawsze klienta {owner.full_name}')
        owner.delete()
        messages.success(request, 'Klient zostal usuniety na zawsze (wraz z psami).')
    return redirect('owner_archived_list')


@login_required
def owner_export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="klienci.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Imie', 'Nazwisko', 'Telefon', 'Email', 'Adres', 'Kontakt zastepczy', 'Telefon zastepczy',
        'Zgoda RODO', 'Zgoda na zdjecia', 'Psy', 'Notatki',
    ])
    owners = Owner.objects.filter(is_active=True).prefetch_related('dogs')
    for owner in owners:
        dog_names = ', '.join(d.name for d in owner.dogs.filter(is_active=True))
        writer.writerow([
            owner.first_name, owner.last_name, owner.phone, owner.email, owner.address,
            owner.secondary_contact_name, owner.secondary_contact_phone,
            'Tak' if owner.rodo_consent else 'Nie',
            'Tak' if owner.photo_consent else 'Nie',
            dog_names, owner.notes,
        ])
    return response


# ============ DOG ============

@login_required
def dog_list(request):
    dogs = Dog.objects.filter(is_active=True).select_related('owner')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        dogs = dogs.filter(
            Q(name__icontains=search_query) |
            Q(breed__icontains=search_query) |
            Q(owner__first_name__icontains=search_query) |
            Q(owner__last_name__icontains=search_query)
        ).distinct()

    status_filter = request.GET.get('status', '').strip()
    if status_filter in (Dog.STATUS_ACTIVE, Dog.STATUS_PAUSED):
        dogs = dogs.filter(training_status=status_filter)

    breed_filter = request.GET.get('breed', '').strip()
    if breed_filter:
        dogs = dogs.filter(breed=breed_filter)

    breed_choices = (
        Dog.objects.filter(is_active=True)
        .exclude(breed='')
        .order_by('breed')
        .values_list('breed', flat=True)
        .distinct()
    )

    paginator = Paginator(dogs, CLIENTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'clients/dog_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'breed_filter': breed_filter,
        'breed_choices': breed_choices,
    })


@login_required
def dog_create(request, owner_pk=None):
    fixed_owner = None
    if owner_pk:
        fixed_owner = get_object_or_404(Owner, pk=owner_pk)

    if request.method == 'POST':
        form = DogForm(request.POST, request.FILES, fixed_owner=fixed_owner)
        if form.is_valid():
            dog = form.save(commit=False)
            if fixed_owner:
                dog.owner = fixed_owner
            dog.save()
            form.save_m2m()
            log_action(request, AuditLog.ACTION_CREATED, AuditLog.TARGET_DOG, dog,
                       f'Dodano psa {dog.name} (wlasciciel: {dog.owner.full_name})')
            messages.success(request, f'Pies {dog.name} zostal dodany.')
            if fixed_owner:
                return redirect('owner_detail', pk=fixed_owner.pk)
            return redirect('dog_detail', pk=dog.pk)
    else:
        form = DogForm(fixed_owner=fixed_owner)

    return render(request, 'clients/dog_form.html', {
        'form': form,
        'title': 'Dodaj psa',
        'fixed_owner': fixed_owner,
    })


@login_required
def dog_update(request, pk):
    dog = get_object_or_404(Dog, pk=pk)
    if request.method == 'POST':
        form = DogForm(request.POST, request.FILES, instance=dog)
        if form.is_valid():
            changed_fields = list(form.changed_data)
            form.save()
            description = f'Zmieniono pola: {", ".join(changed_fields)}' if changed_fields else 'Zapisano (brak zmian danych)'
            log_action(request, AuditLog.ACTION_UPDATED, AuditLog.TARGET_DOG, dog, description)
            messages.success(request, 'Dane psa zostaly zaktualizowane.')
            return redirect('dog_detail', pk=dog.pk)
    else:
        form = DogForm(instance=dog)
    return render(request, 'clients/dog_form.html', {
        'form': form,
        'title': 'Edytuj psa',
        'dog': dog,
    })


@login_required
def dog_detail(request, pk):
    dog = get_object_or_404(Dog, pk=pk)
    training_history = dog.bookings.select_related('session').order_by(
        '-session__date', '-session__start_time'
    )[:20]
    return render(request, 'clients/dog_detail.html', {
        'dog': dog,
        'training_history': training_history,
    })


@login_required
def dog_delete(request, pk):
    dog = get_object_or_404(Dog, pk=pk)
    if request.method == 'POST':
        dog.is_active = False
        dog.save()
        log_action(request, AuditLog.ACTION_ARCHIVED, AuditLog.TARGET_DOG, dog,
                   f'Zarchiwizowano psa {dog.name}')
        messages.success(request, 'Pies zostal przeniesiony do archiwum.')
        return redirect('owner_detail', pk=dog.owner.pk)
    return render(request, 'clients/dog_confirm_delete.html', {'dog': dog})


@login_required
def dog_archived_list(request):
    dogs = Dog.objects.filter(is_active=False).select_related('owner').order_by('-updated_at')
    return render(request, 'clients/dog_archived_list.html', {'dogs': dogs})


@login_required
def dog_restore(request, pk):
    dog = get_object_or_404(Dog, pk=pk, is_active=False)
    if request.method == 'POST':
        dog.is_active = True
        dog.save()
        log_action(request, AuditLog.ACTION_RESTORED, AuditLog.TARGET_DOG, dog,
                   f'Przywrocono psa {dog.name}')
        messages.success(request, 'Pies zostal przywrocony.')
    return redirect('dog_archived_list')


@login_required
def dog_delete_permanent(request, pk):
    dog = get_object_or_404(Dog, pk=pk, is_active=False)
    if request.method == 'POST':
        log_action(request, AuditLog.ACTION_DELETED_PERMANENT, AuditLog.TARGET_DOG, dog,
                   f'Usunieto na zawsze psa {dog.name}')
        dog.delete()
        messages.success(request, 'Pies zostal usuniety na zawsze.')
    return redirect('dog_archived_list')


@login_required
def dog_toggle_training_status(request, pk):
    dog = get_object_or_404(Dog, pk=pk)
    if request.method == 'POST':
        if dog.training_status == Dog.STATUS_ACTIVE:
            dog.training_status = Dog.STATUS_PAUSED
            messages.success(request, f'Trening {dog.name} zostal wstrzymany.')
        else:
            dog.training_status = Dog.STATUS_ACTIVE
            messages.success(request, f'Trening {dog.name} zostal przywrocony (aktywny).')
        dog.save()
        log_action(request, AuditLog.ACTION_STATUS_TOGGLED, AuditLog.TARGET_DOG, dog,
                   f'Zmieniono status treningowy na: {dog.get_training_status_display()}')
    return redirect(request.META.get('HTTP_REFERER', 'dog_list'))


@login_required
def dog_export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="psy.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Imie psa', 'Rasa', 'Plec', 'Wiek', 'Waga (kg)', 'Status treningowy',
        'Wlasciciel', 'Telefon wlasciciela', 'Informacje zdrowotne',
    ])
    dogs = Dog.objects.filter(is_active=True).select_related('owner')
    for dog in dogs:
        writer.writerow([
            dog.name, dog.breed, dog.get_sex_display() if dog.sex else '',
            dog.get_age_display() or '', dog.weight_kg or '',
            dog.get_training_status_display(),
            dog.owner.full_name, dog.owner.phone, dog.health_notes,
        ])
    return response


@login_required
def dog_pdf(request, pk):
    """Generuje jednostronicowa karte psa w PDF (do wydruku / zabrania na
    trening) - zdjecie + podstawowe dane + kontakt + informacje zdrowotne.

    Uzywa wspolnego modulu dogfitness.pdf_fonts (fonty TTF DejaVu) - takie
    same jak w plans/document_generation.py - zeby polskie znaki
    diakrytyczne (ą, ć, ę, ł, ń, ó, ś, ź, ż) renderowaly sie poprawnie
    (NIE transliterujemy ich juz na ASCII jak wczesniej)."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle

    from dogfitness.pdf_fonts import get_pdf_fonts, content_disposition

    dog = get_object_or_404(Dog, pk=pk)
    font_name, font_bold = get_pdf_fonts('Helvetica')

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    style_title = ParagraphStyle('title_pl', fontName=font_bold, fontSize=20, leading=24)
    style_normal = ParagraphStyle('normal_pl', fontName=font_name, fontSize=12, leading=16)
    style_section = ParagraphStyle('section_pl', fontName=font_bold, fontSize=12, leading=16, spaceBefore=6)

    elements = [Paragraph(f"Karta psa: {dog.name}", style_title), Spacer(1, 6 * mm)]

    if dog.photo and dog.photo.name and os.path.exists(dog.photo.path):
        try:
            elements.append(RLImage(dog.photo.path, width=45 * mm, height=45 * mm, kind='proportional'))
            elements.append(Spacer(1, 4 * mm))
        except Exception:
            pass

    def info_line(label, value):
        if value:
            elements.append(Paragraph(f"<b>{label}:</b> {value}", style_normal))

    info_line("Rasa", dog.breed)
    info_line("Plec", dog.get_sex_display() if dog.sex else "")
    info_line("Wiek", dog.get_age_display())
    info_line("Waga", f"{dog.weight_kg} kg" if dog.weight_kg else "")
    info_line("Status treningowy", dog.get_training_status_display())

    elements.append(Spacer(1, 3 * mm))
    info_line("Wlasciciel", dog.owner.full_name)
    info_line("Telefon", dog.owner.phone)
    if dog.owner.secondary_contact_phone:
        info_line("Kontakt zastepczy", f"{dog.owner.secondary_contact_name} - {dog.owner.secondary_contact_phone}")

    def info_paragraph(title, text):
        if not text:
            return
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(title, style_section))
        elements.append(Paragraph(text.replace(chr(10), '<br/>'), style_normal))

    info_paragraph("Informacje zdrowotne:", dog.health_notes)
    info_paragraph("Notatki trenera:", dog.trainer_notes)

    doc.build(elements)
    buf.seek(0)

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = content_disposition('inline', f'karta_{dog.name}.pdf')
    return response


# ============ AUDIT LOG (Dziennik zmian) ============

@login_required
def audit_log_list(request):
    logs = AuditLog.objects.select_related('user').all()

    target_filter = request.GET.get('target', '').strip()
    if target_filter in (AuditLog.TARGET_OWNER, AuditLog.TARGET_DOG):
        logs = logs.filter(target_type=target_filter)

    action_filter = request.GET.get('action', '').strip()
    valid_actions = [choice[0] for choice in AuditLog.ACTION_CHOICES]
    if action_filter in valid_actions:
        logs = logs.filter(action=action_filter)

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'clients/audit_log_list.html', {
        'page_obj': page_obj,
        'target_filter': target_filter,
        'action_filter': action_filter,
        'target_choices': AuditLog.TARGET_CHOICES,
        'action_choices': AuditLog.ACTION_CHOICES,
    })
