from django import forms
from .models import MuscleGroup, Equipment


class MuscleGroupForm(forms.ModelForm):
    class Meta:
        model = MuscleGroup
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
from .models import Exercise


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = [
            'name', 'description', 'video_url',
            'muscle_groups', 'difficulty', 'equipment',
            'contraindications'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/...'}),
            'muscle_groups': forms.CheckboxSelectMultiple(),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'equipment': forms.CheckboxSelectMultiple(),
            'contraindications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Prosty widget pozwalający wybrać wiele plików naraz w <input type="file">
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class ExerciseImageUploadForm(forms.Form):
    images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={'class': 'form-control', 'multiple': True})
    )