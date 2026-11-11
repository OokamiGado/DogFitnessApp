from django import forms
from django.core.exceptions import ValidationError
from clients.models import Owner
from scheduling.models import Booking
from .models import PricingPlan, Payment


class PricingPlanForm(forms.ModelForm):
    class Meta:
        model = PricingPlan
        fields = ['name', 'price', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Trening indywidualny 60 min'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'np. 150.00'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opis (opcjonalnie)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_price(self):
        value = self.cleaned_data.get('price')
        if value is not None and value <= 0:
            raise ValidationError('Cena musi byc wieksza od zera.')
        return value


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['owner', 'booking', 'pricing_plan', 'amount', 'payment_date', 'method', 'status', 'description', 'notes']
        widgets = {
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'booking': forms.Select(attrs={'class': 'form-select'}),
            'pricing_plan': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'method': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Karnet 10 wizyt'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, fixed_owner=None, fixed_booking=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['owner'].queryset = Owner.objects.filter(is_active=True).order_by('last_name', 'first_name')
        self.fields['booking'].required = False
        self.fields['booking'].queryset = Booking.objects.none()
        self.fields['pricing_plan'].required = False
        self.fields['pricing_plan'].queryset = PricingPlan.objects.filter(is_active=True)

        if fixed_owner is not None:
            self.fields['owner'].initial = fixed_owner.pk
            self.fields['owner'].widget = forms.HiddenInput()
            self.fields['booking'].queryset = Booking.objects.filter(
                dog__owner=fixed_owner
            ).exclude(status=Booking.STATUS_CANCELLED).select_related('session', 'dog').order_by('-session__date')

        if fixed_booking is not None:
            # WAZNE: queryset musi zawierac fixed_booking, inaczej walidacja
            # pola (HiddenInput, ale wciaz ModelChoiceField) odrzuci wartosc
            # jako "niepoprawny wybor", nawet gdy jest ustawiona jako initial.
            self.fields['booking'].queryset = Booking.objects.filter(pk=fixed_booking.pk)
            self.fields['booking'].initial = fixed_booking.pk
            self.fields['booking'].widget = forms.HiddenInput()
            self.fields['owner'].initial = fixed_booking.dog.owner.pk
            self.fields['owner'].widget = forms.HiddenInput()

    def clean_amount(self):
        value = self.cleaned_data.get('amount')
        if value is not None and value <= 0:
            raise ValidationError('Kwota musi byc wieksza od zera.')
        return value
