from datetime import date, timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone


class TrainingSession(models.Model):
    """Termin zajec treningowych - slot czasowy, do ktorego trener
    przypisuje rezerwacje (Booking). Jeden termin moze obslugiwac
    zarowno trening indywidualny (capacity=1), jak i grupowy (capacity>1)
    - bez potrzeby dwoch roznych modeli."""

    STATUS_SCHEDULED = 'scheduled'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Zaplanowany'),
        (STATUS_CANCELLED, 'Odwolany'),
        (STATUS_COMPLETED, 'Zakonczony'),
    ]

    title = models.CharField(max_length=200, blank=True, verbose_name="Nazwa (opcjonalnie)",
                              help_text='np. "Trening grupowy - sobota"')
    date = models.DateField(verbose_name="Data")
    start_time = models.TimeField(verbose_name="Godzina rozpoczecia")
    end_time = models.TimeField(verbose_name="Godzina zakonczenia")
    location = models.CharField(max_length=200, blank=True, verbose_name="Miejsce")
    capacity = models.PositiveSmallIntegerField(default=1, verbose_name="Liczba miejsc",
                                                 help_text="1 = trening indywidualny, >1 = grupowy")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SCHEDULED,
                               verbose_name="Status")
    is_public = models.BooleanField(default=False, verbose_name="Widoczny publicznie",
                                     help_text="Funkcja na przyszlosc - publiczny formularz zapisow.")
    notes = models.TextField(blank=True, verbose_name="Notatki trenera")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = "Termin zajec"
        verbose_name_plural = "Terminy zajec"

    def __str__(self):
        label = self.title or "Trening"
        return f"{label} - {self.date.strftime('%d.%m.%Y')} {self.start_time.strftime('%H:%M')}"

    def active_bookings(self):
        """Rezerwacje nie-odwolane (confirmed + waiting_list)."""
        return self.bookings.exclude(status=Booking.STATUS_CANCELLED)

    def confirmed_bookings(self):
        return self.bookings.filter(status=Booking.STATUS_CONFIRMED)

    def waiting_list_bookings(self):
        return self.bookings.filter(status=Booking.STATUS_WAITING_LIST).order_by('created_at')

    def confirmed_count(self):
        return self.confirmed_bookings().count()

    def available_slots(self):
        return max(self.capacity - self.confirmed_count(), 0)

    def is_full(self):
        return self.confirmed_count() >= self.capacity

    def get_conflicting_sessions(self):
        """Zwraca inne AKTYWNE terminy tego samego dnia, ktore sie
        czasowo nakladaja z tym terminem. Uzywane do NIEBLOKUJACEGO
        ostrzezenia - trener moze swiadomie zignorowac (np. dwoje
        psow jednoczesnie z dwoma trenerami, inna sala itp.)."""
        qs = TrainingSession.objects.filter(
            date=self.date, status=self.STATUS_SCHEDULED,
        ).exclude(pk=self.pk)
        conflicts = []
        for other in qs:
            if self.start_time < other.end_time and self.end_time > other.start_time:
                conflicts.append(other)
        return conflicts

    def duplicate_next_week(self):
        """Tworzy kopie tego terminu przesunieta o 7 dni (ta sama godzina,
        pojemnosc, miejsce). NIE kopiuje rezerwacji - nowy termin startuje
        pusty. Uzywane przez przycisk 'Powiel termin'."""
        return TrainingSession.objects.create(
            title=self.title,
            date=self.date + timedelta(days=7),
            start_time=self.start_time,
            end_time=self.end_time,
            location=self.location,
            capacity=self.capacity,
            status=self.STATUS_SCHEDULED,
            is_public=self.is_public,
            notes=self.notes,
        )

    def cancel(self):
        """Odwoluje caly termin ORAZ kaskadowo wszystkie jego aktywne
        rezerwacje (confirmed + waiting_list) - konsystentny stan."""
        self.status = self.STATUS_CANCELLED
        self.save()
        self.active_bookings().update(status=Booking.STATUS_CANCELLED)

    def is_publicly_bookable(self):
        """Czy ten termin moze byc wyswietlony/zarezerwowany przez goscia
        na publicznej stronie zapisow (Etap 4). Wymaga: is_public=True,
        status='scheduled' (nie odwolany/zakonczony) i data nie z
        przeszlosci."""
        return self.is_public and self.status == self.STATUS_SCHEDULED and self.date >= date.today()


class Booking(models.Model):
    """Rezerwacja konkretnego psa na konkretny termin (TrainingSession).
    ZAWSZE wskazuje na realny rekord Dog/Owner (nawet gdy dodawany jest
    'nowy klient' przez trenera - tworzymy prawdziwy Owner+Dog, zero
    tymczasowych/duchowych rekordow) - dzieki temu cala logika
    (historia, kontakt, plany treningowe) dziala jednolicie."""

    STATUS_CONFIRMED = 'confirmed'
    STATUS_WAITING_LIST = 'waiting_list'
    STATUS_CANCELLED = 'cancelled'
    STATUS_ATTENDED = 'attended'
    STATUS_NO_SHOW = 'no_show'
    STATUS_CHOICES = [
        (STATUS_CONFIRMED, 'Zapisany'),
        (STATUS_WAITING_LIST, 'Lista rezerwowa'),
        (STATUS_CANCELLED, 'Odwolany'),
        (STATUS_ATTENDED, 'Obecny'),
        (STATUS_NO_SHOW, 'Nieobecny'),
    ]

    session = models.ForeignKey(TrainingSession, related_name='bookings', on_delete=models.CASCADE,
                                 verbose_name="Termin")
    dog = models.ForeignKey('clients.Dog', related_name='bookings', on_delete=models.CASCADE,
                             verbose_name="Pies")
    linked_plan = models.ForeignKey('plans.TrainingPlan', null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='bookings', verbose_name="Powiazany plan treningowy")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_CONFIRMED,
                               verbose_name="Status")
    notes = models.TextField(blank=True, verbose_name="Notatki")
    journal_entry = models.TextField(blank=True, verbose_name="Notatka z treningu (dziennik)",
                                      help_text="Co robilismy, reakcja psa, co poprawic nastepnym razem - "
                                                 "wypelniane PO odbytym treningu, mozna uzupelnic pozniej.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Rezerwacja"
        verbose_name_plural = "Rezerwacje"

    def __str__(self):
        return f"{self.dog.name} - {self.session}"

    def has_journal_entry(self):
        return bool(self.journal_entry.strip())

    def promote_from_waiting_list_if_needed(self):
        """Jesli ten Booking przechodzi w stan 'cancelled' (lub 'no_show'),
        a na liscie rezerwowej czeka ktos - przesuwamy najdluzej czekajaca
        osobe (FIFO wg created_at) na zwolnione miejsce. Zwraca
        awansowany Booking albo None."""
        session = self.session
        if session.is_full():
            return None
        next_in_line = session.waiting_list_bookings().first()
        if next_in_line:
            next_in_line.status = Booking.STATUS_CONFIRMED
            next_in_line.save()
            return next_in_line
        return None


def split_full_name(full_name):
    """Dzieli 'Jan Kowalski' na ('Jan', 'Kowalski'). Jesli podano tylko
    jedno slowo, zwraca (slowo, ''). Uzywane przy zatwierdzaniu wniosku
    goscia (ktory podaje imie+nazwisko w jednym polu), zeby wypelnic
    Owner.first_name / Owner.last_name."""
    parts = (full_name or '').strip().split()
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], ' '.join(parts[1:])


class PendingBookingRequest(models.Model):
    """Wniosek o rezerwacje zlozony PRZEZ GOScIA (formularz publiczny -
    Etap 4). KWARANTANNA: dopoki trener nie zatwierdzi wniosku, w
    systemie NIE ISTNIEJE zaden Owner/Dog/Booking - to tylko 'papierowy
    wniosek' do recznej weryfikacji czlowieka.

    Zasada: trener jest JEDYNYM punktem, w ktorym dane od goscia staja
    sie prawdziwym klientem w bazie (ochrona przed smieciowymi/falszywymi
    zgloszeniami bez automatycznego tworzenia rekordow)."""

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Czeka na weryfikacje'),
        (STATUS_APPROVED, 'Zatwierdzony'),
        (STATUS_REJECTED, 'Odrzucony'),
    ]

    session = models.ForeignKey(TrainingSession, related_name='pending_requests', on_delete=models.CASCADE,
                                 verbose_name="Termin")

    # Dane podane PRZEZ goscia - surowe, niezweryfikowane
    submitted_name = models.CharField(max_length=200, verbose_name="Imie i nazwisko (podane przez goscia)")
    submitted_phone = models.CharField(max_length=30, verbose_name="Telefon (podany przez goscia)")
    submitted_email = models.EmailField(blank=True, verbose_name="Email (podany przez goscia)")
    dog_name = models.CharField(max_length=100, verbose_name="Imie psa (podane przez goscia)")
    message = models.TextField(blank=True, verbose_name="Wiadomosc od goscia")
    rodo_consent = models.BooleanField(default=False, verbose_name="Zgoda RODO (zaznaczona przez goscia)")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING,
                               verbose_name="Status")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, verbose_name="Zweryfikowane przez")
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="Data weryfikacji")
    rejection_note = models.CharField(max_length=255, blank=True,
                                       verbose_name="Wewnetrzna notatka (np. powod odrzucenia)")

    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adres IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data zgloszenia")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Wniosek o rezerwacje (gosc)"
        verbose_name_plural = "Wnioski o rezerwacje (goscie)"

    def __str__(self):
        return f"{self.submitted_name} - {self.session} ({self.get_status_display()})"

    @classmethod
    def count_recent_from_ip(cls, ip_address, minutes=60):
        """Liczba wnioskow zlozonych z danego IP w ostatnich N minutach -
        uzywane do limitu antyspamowego (domyslnie max 3/godzine)."""
        if not ip_address:
            return 0
        cutoff = timezone.now() - timedelta(minutes=minutes)
        return cls.objects.filter(ip_address=ip_address, created_at__gte=cutoff).count()

    @classmethod
    def has_pending_duplicate(cls, session, phone):
        """Czy juz istnieje NIEZWERYFIKOWANY wniosek na ten termin z tego
        samego numeru telefonu - blokuje wielokrotne zgloszenia tej samej
        osoby na ten sam termin zanim trener zdazy je rozpatrzyc."""
        return cls.objects.filter(
            session=session, submitted_phone=phone, status=cls.STATUS_PENDING
        ).exists()

    def approve(self, user):
        """Zatwierdza wniosek: znajduje istniejacego Owner po telefonie
        (NIE tworzy duplikatu) lub tworzy nowego Owner+Dog, nastepnie
        tworzy Booking (status zalezny od aktualnej pojemnosci terminu -
        moglo sie to zmienic od czasu zgloszenia). Zwraca slownik z
        wynikiem (booking, czy_dopasowano_istniejacego_wlasciciela) do
        wyswietlenia odpowiedniego komunikatu w widoku.

        WAZNE: jesli status wniosku NIE jest 'pending' (juz rozpatrzony),
        rzuca ValueError - zabezpieczenie przed podwojnym zatwierdzeniem."""
        if self.status != self.STATUS_PENDING:
            raise ValueError('Ten wniosek zostal juz rozpatrzony.')

        from clients.models import Owner, Dog

        existing_owner = Owner.objects.filter(phone=self.submitted_phone, is_active=True).first()
        if existing_owner:
            owner = existing_owner
            if self.rodo_consent and not owner.rodo_consent:
                owner.rodo_consent = True
                owner.save()
        else:
            first_name, last_name = split_full_name(self.submitted_name)
            owner = Owner.objects.create(
                first_name=first_name or self.submitted_name,
                last_name=last_name,
                phone=self.submitted_phone,
                email=self.submitted_email,
                rodo_consent=self.rodo_consent,
            )

        dog = Dog.objects.create(owner=owner, name=self.dog_name)

        booking_status = Booking.STATUS_WAITING_LIST if self.session.is_full() else Booking.STATUS_CONFIRMED
        booking = Booking.objects.create(
            session=self.session, dog=dog, status=booking_status, notes=self.message,
        )

        self.status = self.STATUS_APPROVED
        self.decided_by = user
        self.decided_at = timezone.now()
        self.save()

        return {
            'booking': booking,
            'matched_existing_owner': existing_owner is not None,
            'owner': owner,
            'dog': dog,
            'went_to_waiting_list': booking_status == Booking.STATUS_WAITING_LIST,
        }

    def reject(self, user, note=''):
        """Odrzuca wniosek - NIE tworzy zadnego Owner/Dog/Booking, zero
        sladu w bazie poza samym wnioskiem (oznaczonym jako rejected)."""
        if self.status != self.STATUS_PENDING:
            raise ValueError('Ten wniosek zostal juz rozpatrzony.')
        self.status = self.STATUS_REJECTED
        self.decided_by = user
        self.decided_at = timezone.now()
        self.rejection_note = note
        self.save()
