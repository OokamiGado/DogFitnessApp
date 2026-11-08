import re
from datetime import date
from django import forms
from django.core.exceptions import ValidationError
from .models import Owner, Dog

MAX_PHOTO_SIZE_MB = 5


class OwnerForm(forms.ModelForm):
    class Meta:
        model = Owner
        fields = [
            'first_name', 'last_name', 'phone', 'email', 'address', 'notes',
            'secondary_contact_name', 'secondary_contact_phone',
            'rodo_consent', 'photo_consent',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Imie'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwisko'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. 600 123 456'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'np. jan@example.com'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. ul. Kwiatowa 5, Warszawa'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notatki, np. preferowany kontakt...'}),
            'secondary_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. partner/partnerka, dziecko'}),
            'secondary_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. 600 999 888'}),
            'rodo_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'photo_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '').strip()
        if len(value) < 2:
            raise ValidationError('Imie musi miec przynajmniej 2 znaki.')
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name', '').strip()
        if len(value) < 2:
            raise ValidationError('Nazwisko musi miec przynajmniej 2 znaki.')
        return value

    def is_phone_suspicious(self):
        phone = self.cleaned_data.get('phone', '')
        digits_only = re.sub(r'\D', '', phone or '')
        return len(digits_only) not in (9, 11, 12)

    def is_phone_duplicate(self):
        """NIEBLOKUJACA walidacja - sprawdza czy inny (aktywny) wlasciciel
        juz ma ten sam numer telefonu. Zwraca znaleziony Owner lub None."""
        phone = self.cleaned_data.get('phone', '')
        if not phone:
            return None
        qs = Owner.objects.filter(phone=phone, is_active=True)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        return qs.first()


class DogForm(forms.ModelForm):
    class Meta:
        model = Dog
        fields = [
            'owner', 'name', 'breed', 'sex', 'birth_date', 'weight_kg',
            'health_notes', 'health_tags', 'trainer_notes', 'photo', 'training_status',
        ]
        widgets = {
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Imie psa'}),
            'breed': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Border Collie'}),
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'np. 22.5'}),
            'health_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Kontuzje, przeciwwskazania...'}),
            'health_tags': forms.CheckboxSelectMultiple(),
            'trainer_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Prywatne notatki trenera...'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'training_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, fixed_owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['owner'].queryset = Owner.objects.filter(is_active=True)
        if fixed_owner is not None:
            self.fields['owner'].initial = fixed_owner.pk
            self.fields['owner'].widget = forms.HiddenInput()
            self.fields['owner'].required = False
        self.fields['health_tags'].required = False

    def clean_name(self):
        value = self.cleaned_data.get('name', '').strip()
        if len(value) < 2:
            raise ValidationError('Imie psa musi miec przynajmniej 2 znaki.')
        return value

    def clean_birth_date(self):
        """BLOKUJACA walidacja - data urodzenia psa nie moze byc z przyszlosci."""
        value = self.cleaned_data.get('birth_date')
        if value and value > date.today():
            raise ValidationError('Data urodzenia nie moze byc z przyszlosci.')
        return value

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and hasattr(photo, 'size'):
            if photo.size > MAX_PHOTO_SIZE_MB * 1024 * 1024:
                raise ValidationError(f'Zdjecie jest za duze (max {MAX_PHOTO_SIZE_MB}MB).')
            content_type = getattr(photo, 'content_type', None)
            if content_type and not content_type.startswith('image/'):
                raise ValidationError('Plik musi byc obrazem.')
        return photo
