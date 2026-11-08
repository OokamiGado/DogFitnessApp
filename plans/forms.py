from django import forms
from django.core.exceptions import ValidationError
from .models import (
    TrainingPlan, ExerciseSet, PlanExercise,
    PlanTemplate, TemplateExerciseSet, TemplatePlanExercise,
    FREQUENCY_PERIOD_CHOICES,
)


class TrainingPlanForm(forms.ModelForm):
    class Meta:
        model = TrainingPlan
        fields = ['name', 'status', 'training_goal', 'safety_rules']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Plan kondycyjny - jesien 2026'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'training_goal': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Na czym skupia sie ten plan...'}),
            'safety_rules': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Jedna zasada na linie...'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 3:
            raise ValidationError('Nazwa planu musi miec przynajmniej 3 znaki.')
        return name


class ExerciseSetForm(forms.ModelForm):
    class Meta:
        model = ExerciseSet
        fields = ['name', 'frequency_min', 'frequency_max', 'frequency_period']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Zestaw 1'}),
            'frequency_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'np. 3', 'min': 0}),
            'frequency_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'opcjonalnie, np. 4', 'min': 0}),
            'frequency_period': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned = super().clean()
        fmin = cleaned.get('frequency_min')
        fmax = cleaned.get('frequency_max')
        if fmin is not None and fmax is not None and fmax < fmin:
            self.add_error('frequency_max', 'Wartosc "do" nie moze byc mniejsza niz "od".')
        return cleaned


class PlanExerciseForm(forms.ModelForm):
    class Meta:
        model = PlanExercise
        fields = ['goal_text', 'execution_text', 'reps_text', 'notes_text']
        widgets = {
            'goal_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Co chcemy osiagnac tym cwiczeniem u tego psa...'}),
            'execution_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Jak wykonac cwiczenie...'}),
            'reps_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. 6-10x, 15-60 sek'}),
            'notes_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Uwagi specyficzne dla tego psa...'}),
        }


class PlanTemplateForm(forms.ModelForm):
    class Meta:
        model = PlanTemplate
        fields = ['name', 'training_goal', 'safety_rules']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Plan dla psa z dysplazja'}),
            'training_goal': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'safety_rules': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 3:
            raise ValidationError('Nazwa szablonu musi miec przynajmniej 3 znaki.')
        return name
