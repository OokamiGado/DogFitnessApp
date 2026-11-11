from datetime import date
from django.conf import settings
from django.db import models


class Owner(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Imie")
    last_name = models.CharField(max_length=100, verbose_name="Nazwisko")
    phone = models.CharField(max_length=30, verbose_name="Telefon")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.CharField(max_length=255, blank=True, verbose_name="Adres")
    notes = models.TextField(blank=True, verbose_name="Notatki")
    is_active = models.BooleanField(default=True, verbose_name="Aktywny")

    secondary_contact_name = models.CharField(
        max_length=100, blank=True, verbose_name="Kontakt zastepczy - imie i nazwisko"
    )
    secondary_contact_phone = models.CharField(
        max_length=30, blank=True, verbose_name="Kontakt zastepczy - telefon"
    )

    rodo_consent = models.BooleanField(
        default=False, verbose_name="Zgoda na przetwarzanie danych osobowych (RODO)"
    )
    rodo_consent_date = models.DateField(
        null=True, blank=True, verbose_name="Data udzielenia zgody RODO"
    )
    photo_consent = models.BooleanField(
        default=False, verbose_name="Zgoda na wykorzystanie zdjec psa (np. social media)"
    )

    is_anonymized = models.BooleanField(
        default=False, verbose_name="Zanonimizowany",
        help_text="Dane osobowe zostaly usuniete (RODO) - psy, plany i dziennik treningowy ZOSTAJA nietkniete."
    )
    anonymized_at = models.DateTimeField(null=True, blank=True, verbose_name="Data anonimizacji")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "Wlasciciel"
        verbose_name_plural = "Wlasciciele"

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def active_dogs(self):
        return self.dogs.filter(is_active=True)

    def save(self, *args, **kwargs):
        if self.rodo_consent and not self.rodo_consent_date:
            self.rodo_consent_date = date.today()
        if not self.rodo_consent:
            self.rodo_consent_date = None
        super().save(*args, **kwargs)

    def anonymize(self):
        """Usuwa dane OSOBOWE wlasciciela (RODO - 'prawo do bycia
        zapomnianym'), ale NIE dotyka psow/planow/rezerwacji/dziennika
        treningowego - te dane merytoryczne NIE sa danymi osobowymi
        czlowieka i pozostaja w calosci nietkniete. Operacja
        nieodwracalna (dane zrodlowe nie sa gdzies zachowane)."""
        from django.utils import timezone
        self.first_name = "Klient"
        self.last_name = f"zanonimizowany #{self.pk}"
        self.phone = ''
        self.email = ''
        self.address = ''
        self.notes = ''
        self.secondary_contact_name = ''
        self.secondary_contact_phone = ''
        self.rodo_consent = False
        self.photo_consent = False
        self.is_anonymized = True
        self.anonymized_at = timezone.now()
        self.save()


class Dog(models.Model):
    SEX_MALE = 'M'
    SEX_FEMALE = 'F'
    SEX_CHOICES = [
        (SEX_MALE, 'Pies (samiec)'),
        (SEX_FEMALE, 'Suczka (samica)'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_PAUSED = 'paused'
    TRAINING_STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Aktywny'),
        (STATUS_PAUSED, 'Wstrzymany (tymczasowo)'),
    ]

    owner = models.ForeignKey(
        Owner, related_name='dogs', on_delete=models.CASCADE, verbose_name="Wlasciciel"
    )
    name = models.CharField(max_length=100, verbose_name="Imie psa")
    breed = models.CharField(max_length=100, blank=True, verbose_name="Rasa")
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True, verbose_name="Plec")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Data urodzenia")
    weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Waga (kg)"
    )
    health_notes = models.TextField(blank=True, verbose_name="Informacje zdrowotne / przeciwwskazania")
    health_tags = models.ManyToManyField(
        'exercises.ContraindicationTag', blank=True, related_name='dogs',
        verbose_name="Tagi zdrowotne (przeciwwskazania)",
        help_text="Uzywane do automatycznych ostrzezen przy ukladaniu planu treningowego."
    )
    trainer_notes = models.TextField(blank=True, verbose_name="Notatki trenera")
    photo = models.ImageField(upload_to='dogs/', blank=True, null=True, verbose_name="Zdjecie")

    training_status = models.CharField(
        max_length=10, choices=TRAINING_STATUS_CHOICES, default=STATUS_ACTIVE,
        verbose_name="Status treningowy"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktywny (archiwizacja)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    MAX_DIMENSION = 1600

    class Meta:
        ordering = ['name']
        verbose_name = "Pies"
        verbose_name_plural = "Psy"

    def __str__(self):
        return self.name

    def get_age_display(self):
        if not self.birth_date:
            return None
        today = date.today()
        if self.birth_date > today:
            return None

        years = today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
        months = (today.year - self.birth_date.year) * 12 + (today.month - self.birth_date.month)
        if today.day < self.birth_date.day:
            months -= 1

        if years < 1:
            m = max(months, 0)
            if m == 0:
                return "poniżej miesiąca"
            elif m == 1:
                return f"{m} miesiąc"
            elif 2 <= m <= 4:
                return f"{m} miesiące"
            else:
                return f"{m} miesięcy"
        else:
            y = years
            if y == 1:
                return f"{y} rok"
            elif 2 <= (y % 10) <= 4 and not (11 <= (y % 100) <= 14):
                return f"{y} lata"
            else:
                return f"{y} lat"

    def get_shared_tags(self, exercise):
        """Zwraca liste tagow wspolnych dla tego psa i podanego cwiczenia
        (Exercise z modulu 'exercises') - uzywane do ostrzezen przy
        dodawaniu cwiczenia do planu treningowego."""
        dog_tag_ids = set(self.health_tags.values_list('pk', flat=True))
        if not dog_tag_ids:
            return []
        exercise_tags = exercise.contraindication_tags.filter(pk__in=dog_tag_ids)
        return list(exercise_tags)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._resize_photo_if_needed()

    def _resize_photo_if_needed(self):
        try:
            from PIL import Image as PILImage
            if not self.photo or not self.photo.name:
                return
            path = self.photo.path
            with PILImage.open(path) as img:
                width, height = img.size
                if width <= self.MAX_DIMENSION and height <= self.MAX_DIMENSION:
                    return
                img = img.convert('RGB') if img.mode in ('RGBA', 'P') else img
                img.thumbnail((self.MAX_DIMENSION, self.MAX_DIMENSION), PILImage.LANCZOS)
                save_kwargs = {'optimize': True}
                fmt = (img.format or 'JPEG')
                if path.lower().endswith(('.jpg', '.jpeg')):
                    save_kwargs['quality'] = 85
                    fmt = 'JPEG'
                img.save(path, format=fmt, **save_kwargs)
        except Exception:
            pass


class AuditLog(models.Model):
    """Dziennik zmian (audit log) dla CALEJ aplikacji - zapisuje KTO i
    KIEDY wykonal jaka akcje na kliencie, psie, planie treningowym,
    szablonie, terminie, rezerwacji lub wnioskiem goscia. Model zyje w
    'clients' (aplikacja najnizszego poziomu w hierarchii zaleznosci),
    a 'plans' i 'scheduling' importuja go stad (ten sam kierunek
    zaleznosci jak przy modelu Dog)."""

    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_ARCHIVED = 'archived'
    ACTION_RESTORED = 'restored'
    ACTION_DELETED_PERMANENT = 'deleted_permanent'
    ACTION_STATUS_TOGGLED = 'status_toggled'
    ACTION_ANONYMIZED = 'anonymized'
    ACTION_CANCELLED = 'cancelled'
    ACTION_DUPLICATED = 'duplicated'
    ACTION_APPROVED = 'approved'
    ACTION_REJECTED = 'rejected'
    ACTION_CHOICES = [
        (ACTION_CREATED, 'Dodano'),
        (ACTION_UPDATED, 'Zaktualizowano'),
        (ACTION_ARCHIVED, 'Zarchiwizowano'),
        (ACTION_RESTORED, 'Przywrocono'),
        (ACTION_DELETED_PERMANENT, 'Usunieto na zawsze'),
        (ACTION_STATUS_TOGGLED, 'Zmieniono status'),
        (ACTION_ANONYMIZED, 'Zanonimizowano'),
        (ACTION_CANCELLED, 'Odwolano'),
        (ACTION_DUPLICATED, 'Powielono'),
        (ACTION_APPROVED, 'Zatwierdzono'),
        (ACTION_REJECTED, 'Odrzucono'),
    ]

    TARGET_OWNER = 'owner'
    TARGET_DOG = 'dog'
    TARGET_PLAN = 'plan'
    TARGET_TEMPLATE = 'template'
    TARGET_SESSION = 'session'
    TARGET_BOOKING = 'booking'
    TARGET_PENDING_REQUEST = 'pending_request'
    TARGET_PAYMENT = 'payment'
    TARGET_PRICING_PLAN = 'pricing_plan'
    TARGET_CHOICES = [
        (TARGET_OWNER, 'Wlasciciel'),
        (TARGET_DOG, 'Pies'),
        (TARGET_PLAN, 'Plan treningowy'),
        (TARGET_TEMPLATE, 'Szablon planu'),
        (TARGET_SESSION, 'Termin zajec'),
        (TARGET_BOOKING, 'Rezerwacja'),
        (TARGET_PENDING_REQUEST, 'Wniosek goscia'),
        (TARGET_PAYMENT, 'Platnosc'),
        (TARGET_PRICING_PLAN, 'Pozycja cennika'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data i czas")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Uzytkownik"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Akcja")
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES, verbose_name="Typ obiektu")
    target_id = models.IntegerField(null=True, blank=True, verbose_name="ID obiektu")
    target_repr = models.CharField(max_length=200, verbose_name="Obiekt (nazwa w momencie akcji)")
    description = models.TextField(blank=True, verbose_name="Opis zmiany")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Wpis dziennika zmian"
        verbose_name_plural = "Dziennik zmian"

    def __str__(self):
        return f"{self.get_action_display()} - {self.target_repr}"
