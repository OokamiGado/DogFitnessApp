from django import forms
from django.core.exceptions import ValidationError
from .models import MuscleGroup, Equipment, Exercise

MAX_IMAGE_SIZE_MB = 5
MAX_IMAGES_COUNT = 10


class MuscleGroupForm(forms.ModelForm):
    class Meta:
        model = MuscleGroup
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Core, Tylne łapy'}),
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Piłka, Step'}),
        }


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = [
            'name', 'description', 'video_url',
            'muscle_groups', 'difficulty', 'equipment',
            'contraindications'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa ćwiczenia'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Opisz jak wykonać ćwiczenie...'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/watch?v=...'}),
            'muscle_groups': forms.CheckboxSelectMultiple(),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'equipment': forms.CheckboxSelectMultiple(),
            'contraindications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Np. nie dla psów z dysplazją stawów...'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 3:
            raise ValidationError('Nazwa musi mieć przynajmniej 3 znaki.')
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if len(description) < 10:
            raise ValidationError('Opis musi mieć przynajmniej 10 znaków - pomóż trenerowi zrozumieć ćwiczenie.')
        return description

    def clean_muscle_groups(self):
        groups = self.cleaned_data.get('muscle_groups')
        if not groups:
            raise ValidationError('Wybierz przynajmniej jedną grupę mięśniową.')
        return groups

    def clean_video_url(self):
        url = self.cleaned_data.get('video_url')
        if url:
            allowed_domains = ['youtube.com', 'youtu.be', 'vimeo.com']
            if not any(domain in url for domain in allowed_domains):
                raise ValidationError('Link do video musi prowadzić do YouTube lub Vimeo.')
        return url


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

    def clean_images(self):
        images = self.cleaned_data.get('images')
        if not images:
            return images

        if not isinstance(images, list):
            images = [images]

        if len(images) > MAX_IMAGES_COUNT:
            raise ValidationError(f'Możesz dodać maksymalnie {MAX_IMAGES_COUNT} zdjęć naraz.')

        for img in images:
            if img.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise ValidationError(f'Plik "{img.name}" jest za duży (max {MAX_IMAGE_SIZE_MB}MB).')
            if not img.content_type.startswith('image/'):
                raise ValidationError(f'Plik "{img.name}" nie jest obrazem.')

        return images