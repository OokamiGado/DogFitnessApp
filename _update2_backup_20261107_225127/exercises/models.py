import re
from django.db import models


class MuscleGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Grupa miesniowa"
        verbose_name_plural = "Grupy miesniowe"

    def __str__(self):
        return self.name


class Equipment(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Sprzet"
        verbose_name_plural = "Sprzet"

    def __str__(self):
        return self.name


class Exercise(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Latwy'),
        ('medium', 'Sredni'),
        ('hard', 'Trudny'),
    ]

    name = models.CharField(max_length=200, verbose_name="Nazwa")
    description = models.TextField(verbose_name="Opis")
    video_url = models.URLField(blank=True, null=True, verbose_name="Link do video", help_text="Link np. do YouTube")
    muscle_groups = models.ManyToManyField(MuscleGroup, related_name='exercises', verbose_name="Grupy miesniowe")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, verbose_name="Poziom trudnosci")
    equipment = models.ManyToManyField(Equipment, blank=True, related_name='exercises', verbose_name="Potrzebny sprzet")
    contraindications = models.TextField(blank=True, verbose_name="Przeciwwskazania")

    parent_exercise = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='variants',
        verbose_name="Wariant cwiczenia"
    )
    variant_name = models.CharField(
        max_length=100, blank=True,
        verbose_name="Nazwa wariantu",
        help_text='np. "Zaawansowany", "Z pilka", "Dla szczeniaka"'
    )

    is_active = models.BooleanField(default=True, verbose_name="Aktywne")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Cwiczenie"
        verbose_name_plural = "Cwiczenia"

    def __str__(self):
        return self.name

    def get_youtube_embed_url(self):
        """Zwraca URL do embedowania video YouTube, albo None jesli to nie YouTube/niepoprawny link"""
        if not self.video_url:
            return None

        patterns = [
            r'(?:youtube\.com\/watch\?v=)([^&\n?#]+)',
            r'(?:youtu\.be\/)([^&\n?#]+)',
            r'(?:youtube\.com\/embed\/)([^&\n?#]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.video_url)
            if match:
                return f'https://www.youtube.com/embed/{match.group(1)}'
        return None

    def active_variants(self):
        """Lista aktywnych wariantow tego cwiczenia (jesli to cwiczenie 'glowne')"""
        return self.variants.filter(is_active=True).order_by('created_at')

    def get_root(self):
        """Zwraca cwiczenie 'glowne' - jesli to wariant, zwraca jego rodzica; jesli samo jest glowne, zwraca siebie"""
        return self.parent_exercise if self.parent_exercise else self

    def get_cover_image(self):
        """Zwraca zdjecie oznaczone jako okladka, albo pierwsze dostepne zdjecie"""
        cover = self.images.filter(is_cover=True).first()
        return cover or self.images.first()


class ExerciseImage(models.Model):
    exercise = models.ForeignKey(Exercise, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='exercises/')
    is_cover = models.BooleanField(default=False, verbose_name="Zdjecie okladkowe")

    def __str__(self):
        return f"Zdjecie dla {self.exercise.name}"
