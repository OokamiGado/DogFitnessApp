import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from .models import Owner, Dog
from .forms import OwnerForm, DogForm

CLIENTS_PER_PAGE = 25

PHONE_WARNING_MSG = 'Numer telefonu moze byc niepoprawny - sprawdz, czy to nie pomylka. Zapisano mimo to.'


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

    paginator = Paginator(owners, CLIENTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    stats = {
        'owners_count': Owner.objects.filter(is_active=True).count(),
        'dogs_count': Dog.objects.filter(is_active=True).count(),
    }

    return render(request, 'clients/owner_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'stats': stats,
    })


@login_required
def owner_create(request):
    if request.method == 'POST':
        form = OwnerForm(request.POST)
        if form.is_valid():
            owner = form.save()
            if form.is_phone_suspicious():
                messages.warning(request, PHONE_WARNING_MSG)
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
    if request.method == 'POST':
        form = OwnerForm(request.POST, instance=owner)
        if form.is_valid():
            form.save()
            if form.is_phone_suspicious():
                messages.warning(request, PHONE_WARNING_MSG)
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
        messages.success(request, 'Klient zostal przywrocony.')
    return redirect('owner_archived_list')


@login_required
def owner_delete_permanent(request, pk):
    owner = get_object_or_404(Owner, pk=pk, is_active=False)
    if request.method == 'POST':
        owner.delete()
        messages.success(request, 'Klient zostal usuniety na zawsze (wraz z psami).')
    return redirect('owner_archived_list')


@login_required
def owner_export_csv(request):
    """Eksport aktywnych klientow do CSV (np. do uzycia offline na telefonie)."""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="klienci.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Imie', 'Nazwisko', 'Telefon', 'Email', 'Kontakt zastepczy', 'Telefon zastepczy',
        'Zgoda RODO', 'Zgoda na zdjecia', 'Psy', 'Notatki',
    ])
    owners = Owner.objects.filter(is_active=True).prefetch_related('dogs')
    for owner in owners:
        dog_names = ', '.join(d.name for d in owner.dogs.filter(is_active=True))
        writer.writerow([
            owner.first_name, owner.last_name, owner.phone, owner.email,
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

    paginator = Paginator(dogs, CLIENTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'clients/dog_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
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
            form.save()
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
    return render(request, 'clients/dog_detail.html', {'dog': dog})


@login_required
def dog_delete(request, pk):
    dog = get_object_or_404(Dog, pk=pk)
    if request.method == 'POST':
        dog.is_active = False
        dog.save()
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
        messages.success(request, 'Pies zostal przywrocony.')
    return redirect('dog_archived_list')


@login_required
def dog_delete_permanent(request, pk):
    dog = get_object_or_404(Dog, pk=pk, is_active=False)
    if request.method == 'POST':
        dog.delete()
        messages.success(request, 'Pies zostal usuniety na zawsze.')
    return redirect('dog_archived_list')


@login_required
def dog_toggle_training_status(request, pk):
    """Szybkie przelaczenie statusu Aktywny <-> Wstrzymany (bez archiwizacji)."""
    dog = get_object_or_404(Dog, pk=pk)
    if request.method == 'POST':
        if dog.training_status == Dog.STATUS_ACTIVE:
            dog.training_status = Dog.STATUS_PAUSED
            messages.success(request, f'Trening {dog.name} zostal wstrzymany.')
        else:
            dog.training_status = Dog.STATUS_ACTIVE
            messages.success(request, f'Trening {dog.name} zostal przywrocony (aktywny).')
        dog.save()
    return redirect(request.META.get('HTTP_REFERER', 'dog_list'))


@login_required
def dog_export_csv(request):
    """Eksport aktywnych psow do CSV."""
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
