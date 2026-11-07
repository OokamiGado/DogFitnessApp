import re
from django.db import models


class MuscleGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Grupa mięśniowa"
        verbose_name_plural = "Grupy mięśniowe"

    def __str__(self):
        return self.name


class Equipment(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Sprzęt"
        verbose_name_plural = "Sprzęt"

    def __str__(self):
        return self.name


class Exercise(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Łatwy'),
        ('medium', 'Średni'),
        ('hard', 'Trudny'),
    ]

    name = models.CharField(max_length=200, verbose_name="Nazwa")
    description = models.TextField(verbose_name="Opis")
    video_url = models.URLField(blank=True, null=True, verbose_name="Link do video", help_text="Link np. do YouTube")
    muscle_groups = models.ManyToManyField(MuscleGroup, related_name='exercises', verbose_name="Grupy mięśniowe")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, verbose_name="Poziom trudności")
    equipment = models.ManyToManyField(Equipment, blank=True, related_name='exercises', verbose_name="Potrzebny sprzęt")
    contraindications = models.TextField(blank=True, verbose_name="Przeciwwskazania")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Ćwiczenie"
        verbose_name_plural = "Ćwiczenia"

    def __str__(self):
        return self.name

    def get_youtube_embed_url(self):
        """Zwraca URL do embedowania video YouTube, albo None jeśli to nie YouTube/niepoprawny link"""
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


class ExerciseImage(models.Model):
    exercise = models.ForeignKey(Exercise, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='exercises/')

    def __str__(self):
        return f"Zdjęcie dla {self.exercise.name}"