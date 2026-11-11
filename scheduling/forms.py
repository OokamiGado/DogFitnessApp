from django import forms
from django.core.exceptions import ValidationError
from clients.models import Owner, Dog
from .models import TrainingSession, Booking


class TrainingSessionForm(forms.ModelForm):
    class Meta:
        model = TrainingSession
        fields = ['title', 'date', 'start_time', 'end_time', 'location', 'capacity', 'status', 'is_public', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Trening grupowy - sobota'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Sala treningowa A'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and end_time <= start_time:
            raise ValidationError('Godzina zakonczenia musi byc po godzinie rozpoczecia.')
        return cleaned_data

    def clean_capacity(self):
        value = self.cleaned_data.get('capacity')
        if value is not None and value < 1:
            raise ValidationError('Liczba miejsc musi byc przynajmniej 1.')
        return value


class BookingForm(forms.ModelForm):
    """Zapisanie ISTNIEJACEGO (juz w bazie) psa na termin."""

    class Meta:
        model = Booking
        fields = ['dog', 'linked_plan', 'notes']
        widgets = {
            'dog': forms.Select(attrs={'class': 'form-select'}),
            'linked_plan': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, session=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.fields['dog'].queryset = Dog.objects.filter(is_active=True).select_related('owner')
        self.fields['linked_plan'].required = False
        self.fields['linked_plan'].queryset = self.fields['linked_plan'].queryset.none()
        self.fields['linked_plan'].help_text = "Wybierz psa, aby zobaczyc jego plany treningowe."

    def clean_dog(self):
        dog = self.cleaned_data.get('dog')
        if dog and self.session:
            already_booked = Booking.objects.filter(
                session=self.session, dog=dog
            ).exclude(status=Booking.STATUS_CANCELLED).exists()
            if already_booked:
                raise ValidationError(f'{dog.name} jest juz zapisany na ten termin.')
        return dog


class NewClientBookingForm(forms.Form):
    """Zapisanie NOWEGO klienta (nieistniejacego jeszcze w bazie) na
    termin - tworzy PRAWDZIWY rekord Owner + Dog (nie 'goscia'), zeby
    cala pozostala logika aplikacji (historia, kontakt, plany) dzialala
    identycznie jak dla istniejacych klientow."""

    first_name = forms.CharField(max_length=100, label="Imie wlasciciela",
                                  widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, label="Nazwisko wlasciciela",
                                 widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=30, label="Telefon",
                             widget=forms.TextInput(attrs={'class': 'form-control'}))
    dog_name = forms.CharField(max_length=100, label="Imie psa",
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    notes = forms.CharField(required=False, label="Notatki",
                             widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))

    def find_existing_owner(self):
        """Szuka istniejacego wlasciciela po numerze telefonu - zeby NIE
        tworzyc duplikatu, jesli stala klientka zapisuje sie ponownie."""
        phone = self.cleaned_data.get('phone', '')
        if not phone:
            return None
        return Owner.objects.filter(phone=phone, is_active=True).first()

    def save_owner_and_dog(self, existing_owner=None):
        """Tworzy (lub reuzywa) Owner + tworzy nowy Dog. Zwraca
        utworzonego/znalezionego psa (Dog)."""
        if existing_owner:
            owner = existing_owner
        else:
            owner = Owner.objects.create(
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                phone=self.cleaned_data['phone'],
            )
        dog = Dog.objects.create(
            owner=owner,
            name=self.cleaned_data['dog_name'],
        )
        return dog



class PublicBookingRequestForm(forms.Form):
    """Formularz PUBLICZNY (bez logowania) - gosc zglasza chec zapisu na
    termin. NIE tworzy zadnego Owner/Dog/Booking bezposrednio - dane
    trafiaja do PendingBookingRequest (kwarantanna), trener recznie
    zatwierdza lub odrzuca.

    Honeypot: pole 'website' jest CALKOWICIE niewidoczne dla czlowieka
    (ukryte przez CSS w szablonie), ale wypelniane automatycznie przez
    wiele prostych botow, ktore wypelniaja kazde pole formularza. Jesli
    to pole ma jakakolwiek wartosc - traktujemy zgloszenie jako spam."""

    submitted_name = forms.CharField(max_length=200, label="Imie i nazwisko",
                                      widget=forms.TextInput(attrs={'class': 'form-control'}))
    submitted_phone = forms.CharField(max_length=30, label="Telefon",
                                       widget=forms.TextInput(attrs={'class': 'form-control'}))
    submitted_email = forms.EmailField(required=False, label="Email (opcjonalnie)",
                                        widget=forms.EmailInput(attrs={'class': 'form-control'}))
    dog_name = forms.CharField(max_length=100, label="Imie psa",
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    message = forms.CharField(required=False, label="Wiadomosc (opcjonalnie)",
                               widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    rodo_consent = forms.BooleanField(
        required=True, label="Zgadzam sie na przetwarzanie moich danych osobowych w celu rezerwacji zajec (RODO)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        error_messages={'required': 'Zgoda RODO jest wymagana, aby zlozyc zgloszenie.'},
    )
    # Honeypot - NIE pokazywany uzytkownikowi (ukryty w CSS szablonu),
    # musi zostac PUSTY. Jesli bot go wypelni - to_mark_as_spam() = True.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'autocomplete': 'off', 'tabindex': '-1',
    }))

    def is_spam(self):
        """True jesli honeypot zostal wypelniony (prawdopodobnie bot)."""
        return bool(self.cleaned_data.get('website', '').strip())



class BookingJournalForm(forms.ModelForm):
    """Formularz notatki z treningu (dziennik treningowy) - wolny tekst,
    wypelniany PO odbytym treningu. Opcjonalny - mozna zapisac puste pole
    i wrocic do niego pozniej (link z karty psa / ze szczegolow terminu)."""

    class Meta:
        model = Booking
        fields = ['journal_entry']
        widgets = {
            'journal_entry': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Co robilismy, jak pies zareagowal, co poprawic nastepnym razem...',
            }),
        }
