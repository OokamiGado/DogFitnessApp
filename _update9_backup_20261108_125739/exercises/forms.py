from django import forms
from django.core.exceptions import ValidationError
from .models import MuscleGroup, Equipment, Exercise

MAX_IMAGE_SIZE_MB = 5
MAX_IMAGES_PER_EXERCISE = 5


class MuscleGroupForm(forms.ModelForm):
    class Meta:
        model = MuscleGroup
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Core, Tylne lapy'}),
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Pilka, Step'}),
        }


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = [
            'name', 'description', 'video_url',
            'muscle_groups', 'difficulty', 'equipment',
            'contraindications', 'parent_exercise', 'variant_name',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa cwiczenia'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Opisz jak wykonac cwiczenie...'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/watch?v=...'}),
            'muscle_groups': forms.CheckboxSelectMultiple(),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'equipment': forms.CheckboxSelectMultiple(),
            'contraindications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Np. nie dla psow z dysplazja stawow...'}),
            'parent_exercise': forms.Select(attrs={'class': 'form-select'}),
            'variant_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Zaawansowany, Z pilka, Dla szczeniaka'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Exercise.objects.filter(parent_exercise__isnull=True, is_active=True)
        if self.instance and self.instance.pk:
            exclude_ids = [self.instance.pk] + list(self.instance.variants.values_list('pk', flat=True))
            qs = qs.exclude(pk__in=exclude_ids)
        self.fields['parent_exercise'].queryset = qs
        self.fields['parent_exercise'].required = False
        self.fields['parent_exercise'].empty_label = "- Samodzielne cwiczenie (nie wariant) -"
        self.fields['variant_name'].required = False

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 3:
            raise ValidationError('Nazwa musi miec przynajmniej 3 znaki.')
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if len(description) < 10:
            raise ValidationError('Opis musi miec przynajmniej 10 znakow - pomoz trenerowi zrozumiec cwiczenie.')
        return description

    def clean_muscle_groups(self):
        groups = self.cleaned_data.get('muscle_groups')
        if not groups:
            raise ValidationError('Wybierz przynajmniej jedna grupe miesniowa.')
        return groups

    def clean_video_url(self):
        url = self.cleaned_data.get('video_url')
        if url:
            allowed_domains = ['youtube.com', 'youtu.be', 'vimeo.com']
            if not any(domain in url for domain in allowed_domains):
                raise ValidationError('Link do video musi prowadzic do YouTube lub Vimeo.')
        return url

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get('parent_exercise')
        variant_name = cleaned.get('variant_name', '').strip()
        if parent and not variant_name:
            self.add_error('variant_name', 'Podaj nazwe wariantu, np. "Zaawansowany" albo "Z pilka".')
        return cleaned


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
    """Formularz uploadu zdjec. Przyjmuje 'existing_count' - liczbe zdjec,
    ktore dane cwiczenie (wariant) juz posiada - zeby wyliczyc limit
    MAX_IMAGES_PER_EXERCISE lacznie (stare + nowe)."""

    images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={'class': 'form-control', 'multiple': True})
    )

    def __init__(self, *args, existing_count=0, **kwargs):
        self.existing_count = existing_count
        super().__init__(*args, **kwargs)

    def clean_images(self):
        images = self.cleaned_data.get('images')
        if not images:
            return images

        if not isinstance(images, list):
            images = [images]

        total_after = self.existing_count + len(images)
        if total_after > MAX_IMAGES_PER_EXERCISE:
            allowed_now = max(MAX_IMAGES_PER_EXERCISE - self.existing_count, 0)
            raise ValidationError(
                f'Ten wariant cwiczenia moze miec maksymalnie {MAX_IMAGES_PER_EXERCISE} zdjec. '
                f'Masz juz {self.existing_count}, mozesz dodac jeszcze {allowed_now}.'
            )

        for img in images:
            if img.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise ValidationError(f'Plik "{img.name}" jest za duzy (max {MAX_IMAGE_SIZE_MB}MB).')
            if not img.content_type.startswith('image/'):
                raise ValidationError(f'Plik "{img.name}" nie jest obrazem.')

        return images
