from decimal import Decimal
from django.db import models
from django.conf import settings


class PricingPlan(models.Model):
    """Cennik trenera - WIDOCZNY TYLKO W PANELU (nigdy na publicznych
    stronach zapisow). Uzywany jako podpowiedz kwoty przy rejestrowaniu
    platnosci, ale kwota platnosci jest zawsze edytowalna recznie
    (np. rabat, pakiet promocyjny, inna domowa ustalona cena)."""

    name = models.CharField(max_length=150, verbose_name="Nazwa cennika",
                             help_text='np. "Trening indywidualny 60 min", "Karnet 10 wizyt"')
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Cena (PLN)")
    description = models.CharField(max_length=255, blank=True, verbose_name="Opis (opcjonalnie)")
    is_active = models.BooleanField(default=True, verbose_name="Aktywny (widoczny do wyboru)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Cennik"
        verbose_name_plural = "Cenniki"

    def __str__(self):
        return f"{self.name} - {self.price} PLN"


class Payment(models.Model):
    """Pojedynczy wplyw/platnosc od klienta. Moze (ale nie musi) byc
    powiazana z konkretna rezerwacja (Booking) - np. platnosc za karnet
    na kilka wizyt na raz nie jest przypisana do jednej sesji, tylko do
    wlasciciela (Owner).

    Zasada: dane finansowe NIGDY nie sa usuwane przy anonimizacji/
    archiwizacji klienta - to wymog podatkowy (ksiegowosc wymaga
    zachowania historii wplywow niezaleznie od statusu klienta)."""

    METHOD_CASH = 'cash'
    METHOD_TRANSFER = 'transfer'
    METHOD_BLIK = 'blik'
    METHOD_CARD = 'card'
    METHOD_OTHER = 'other'
    METHOD_CHOICES = [
        (METHOD_CASH, 'Gotowka'),
        (METHOD_TRANSFER, 'Przelew'),
        (METHOD_BLIK, 'BLIK'),
        (METHOD_CARD, 'Karta'),
        (METHOD_OTHER, 'Inna'),
    ]

    STATUS_PAID = 'paid'
    STATUS_PENDING = 'pending'
    STATUS_CHOICES = [
        (STATUS_PAID, 'Oplacone'),
        (STATUS_PENDING, 'Oczekuje na platnosc'),
    ]

    owner = models.ForeignKey(
        'clients.Owner', related_name='payments', on_delete=models.PROTECT,
        verbose_name="Klient",
        help_text="Platnosc jest ZAWSZE powiazana z klientem (nawet jesli tez z konkretna sesja) - "
                   "umozliwia to zestawienia 'kto ile zaplacil' niezaleznie od tego, czy sesja istnieje."
    )
    booking = models.ForeignKey(
        'scheduling.Booking', null=True, blank=True, related_name='payments', on_delete=models.SET_NULL,
        verbose_name="Powiazana rezerwacja (opcjonalnie)",
        help_text="Zostaw puste dla platnosci za karnet / kilka wizyt na raz."
    )
    pricing_plan = models.ForeignKey(
        PricingPlan, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Pozycja cennika (opcjonalnie, tylko podpowiedz)"
    )

    amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Kwota (PLN)")
    payment_date = models.DateField(verbose_name="Data platnosci")
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default=METHOD_CASH, verbose_name="Metoda platnosci")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PAID, verbose_name="Status")
    description = models.CharField(max_length=255, blank=True, verbose_name="Opis",
                                    help_text='np. "Karnet 10 wizyt - styczen 2026"')
    notes = models.TextField(blank=True, verbose_name="Notatki")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Zarejestrowane przez"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = "Platnosc"
        verbose_name_plural = "Platnosci"

    def __str__(self):
        return f"{self.owner.full_name} - {self.amount} PLN ({self.payment_date.strftime('%d.%m.%Y')})"

    @property
    def is_paid(self):
        return self.status == self.STATUS_PAID
