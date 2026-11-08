from django.db import models


FREQUENCY_PERIOD_CHOICES = [
    ('day', 'dziennie'),
    ('week', 'w tygodniu'),
    ('month', 'w miesiacu'),
]


def format_frequency(freq_min, freq_max, period):
    """Buduje czytelny tekst czestotliwosci, np. '3x w tygodniu' albo
    '0-1x w tygodniu'. Zwraca pusty string jesli brak danych."""
    if freq_min is None and freq_max is None:
        return ''
    period_label = dict(FREQUENCY_PERIOD_CHOICES).get(period, period)
    if freq_max is None or freq_max == freq_min:
        value = freq_min if freq_min is not None else freq_max
        return f"{value}x {period_label}"
    if freq_min is None:
        return f"{freq_max}x {period_label}"
    return f"{freq_min}-{freq_max}x {period_label}"


class PlanTemplate(models.Model):
    """Szablon planu treningowego - wielokrotnego uzytku. Trener moze
    'wystartowac' od szablonu tworzac nowy plan dla konkretnego psa -
    dane sa KOPIOWANE (nie linkowane), wiec modyfikacje planu NIE wplywaja
    na szablon i odwrotnie."""
    name = models.CharField(max_length=200, verbose_name="Nazwa szablonu")
    training_goal = models.TextField(blank=True, verbose_name="Cel treningu")
    safety_rules = models.TextField(blank=True, verbose_name="Wazne zasady i bezpieczenstwo")
    is_active = models.BooleanField(default=True, verbose_name="Aktywny")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Szablon planu"
        verbose_name_plural = "Szablony planow"

    def __str__(self):
        return self.name


class TemplateExerciseSet(models.Model):
    """Zestaw cwiczen wewnatrz szablonu planu (np. 'Zestaw 1')."""
    template = models.ForeignKey(
        PlanTemplate, related_name='exercise_sets', on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100, verbose_name="Nazwa zestawu", default="Zestaw 1")
    frequency_min = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Czestotliwosc od")
    frequency_max = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Czestotliwosc do")
    frequency_period = models.CharField(
        max_length=10, choices=FREQUENCY_PERIOD_CHOICES, default='week', verbose_name="Okres"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Kolejnosc")

    class Meta:
        ordering = ['order', 'pk']
        verbose_name = "Zestaw cwiczen (szablon)"
        verbose_name_plural = "Zestawy cwiczen (szablon)"

    def __str__(self):
        return f"{self.name} ({self.template.name})"

    def get_frequency_display_text(self):
        return format_frequency(self.frequency_min, self.frequency_max, self.frequency_period)


class TemplatePlanExercise(models.Model):
    """Pozycja cwiczenia wewnatrz zestawu szablonu."""
    exercise_set = models.ForeignKey(
        TemplateExerciseSet, related_name='plan_exercises', on_delete=models.CASCADE
    )
    exercise = models.ForeignKey(
        'exercises.Exercise', on_delete=models.PROTECT, related_name='template_usages',
        verbose_name="Cwiczenie"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Kolejnosc")
    goal_text = models.TextField(blank=True, verbose_name="Cel")
    execution_text = models.TextField(blank=True, verbose_name="Wykonanie")
    reps_text = models.CharField(max_length=255, blank=True, verbose_name="Ilosc / powtorzenia")
    notes_text = models.TextField(blank=True, verbose_name="Uwagi")

    class Meta:
        ordering = ['order', 'pk']
        verbose_name = "Cwiczenie w zestawie (szablon)"
        verbose_name_plural = "Cwiczenia w zestawach (szablon)"

    def __str__(self):
        return f"{self.exercise.name} w {self.exercise_set}"


class TrainingPlan(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Szkic'),
        (STATUS_ACTIVE, 'Aktywny'),
        (STATUS_COMPLETED, 'Zakonczony'),
    ]

    dog = models.ForeignKey(
        'clients.Dog', related_name='training_plans', on_delete=models.CASCADE, verbose_name="Pies"
    )
    name = models.CharField(max_length=200, verbose_name="Nazwa planu")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name="Status"
    )
    training_goal = models.TextField(blank=True, verbose_name="Cel treningu")
    safety_rules = models.TextField(blank=True, verbose_name="Wazne zasady i bezpieczenstwo")
    created_from_template = models.ForeignKey(
        PlanTemplate, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='plans_created', verbose_name="Utworzony z szablonu"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktywny (archiwizacja)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Plan treningowy"
        verbose_name_plural = "Plany treningowe"

    def __str__(self):
        return f"{self.name} ({self.dog.name})"

    def get_conflicts(self):
        """Zwraca liste (plan_exercise, shared_tags) dla kazdego cwiczenia
        w tym planie, ktore ma wspolny tag zdrowotny z psem. Uzywane do
        ostrzezen na stronie planu/psa."""
        conflicts = []
        for ex_set in self.exercise_sets.all():
            for pe in ex_set.plan_exercises.all():
                shared = self.dog.get_shared_tags(pe.exercise)
                if shared:
                    conflicts.append((pe, shared))
        return conflicts


class ExerciseSet(models.Model):
    """Zestaw cwiczen wewnatrz konkretnego planu treningowego psa."""
    plan = models.ForeignKey(
        TrainingPlan, related_name='exercise_sets', on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100, verbose_name="Nazwa zestawu", default="Zestaw 1")
    frequency_min = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Czestotliwosc od")
    frequency_max = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Czestotliwosc do")
    frequency_period = models.CharField(
        max_length=10, choices=FREQUENCY_PERIOD_CHOICES, default='week', verbose_name="Okres"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Kolejnosc")

    class Meta:
        ordering = ['order', 'pk']
        verbose_name = "Zestaw cwiczen"
        verbose_name_plural = "Zestawy cwiczen"

    def __str__(self):
        return f"{self.name} ({self.plan.name})"

    def get_frequency_display_text(self):
        return format_frequency(self.frequency_min, self.frequency_max, self.frequency_period)


class PlanExercise(models.Model):
    """Pozycja cwiczenia wewnatrz zestawu konkretnego planu."""
    exercise_set = models.ForeignKey(
        ExerciseSet, related_name='plan_exercises', on_delete=models.CASCADE
    )
    exercise = models.ForeignKey(
        'exercises.Exercise', on_delete=models.PROTECT, related_name='plan_usages',
        verbose_name="Cwiczenie"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Kolejnosc")
    goal_text = models.TextField(blank=True, verbose_name="Cel")
    execution_text = models.TextField(blank=True, verbose_name="Wykonanie")
    reps_text = models.CharField(max_length=255, blank=True, verbose_name="Ilosc / powtorzenia")
    notes_text = models.TextField(blank=True, verbose_name="Uwagi")

    class Meta:
        ordering = ['order', 'pk']
        verbose_name = "Cwiczenie w zestawie"
        verbose_name_plural = "Cwiczenia w zestawach"

    def __str__(self):
        return f"{self.exercise.name} w {self.exercise_set}"


class BrandingProfile(models.Model):
    """Szablon wizualny (branding) uzywany przy generowaniu dokumentow
    PDF/DOCX (plan szczegolowy, fiszka treningowa) - Etap 4. Trener moze
    miec wiele profili, ale tylko JEDEN moze byc oznaczony jako domyslny
    (is_default) - ten jest uzywany automatycznie przy generowaniu
    dokumentow, jesli nie wybrano innego."""

    FONT_CHOICES = [
        ('Helvetica', 'Helvetica (nowoczesna, bezszeryfowa)'),
        ('Times-Roman', 'Times (klasyczna, szeryfowa)'),
        ('Courier', 'Courier (maszynowa)'),
    ]

    name = models.CharField(max_length=100, verbose_name="Nazwa profilu", default="Domyslny")
    logo = models.ImageField(upload_to='branding/', blank=True, null=True, verbose_name="Logo")
    primary_color = models.CharField(
        max_length=7, default="#D9D9D9", verbose_name="Kolor belek sekcji",
        help_text="Kolor HEX, np. #D9D9D9 (jak w oryginalnych dokumentach Pauli)"
    )
    text_color = models.CharField(
        max_length=7, default="#000000", verbose_name="Kolor tekstu naglowkow",
        help_text="Kolor HEX tekstu na belkach sekcji"
    )
    font_family = models.CharField(
        max_length=20, choices=FONT_CHOICES, default='Helvetica', verbose_name="Czcionka"
    )
    footer_text = models.CharField(
        max_length=255, blank=True,
        default="Pamietaj o rozgrzewce i cooldownie - antyposlizgowa nawierzchnia - jakosc > liczba powtorzen",
        verbose_name="Tekst w stopce"
    )
    is_default = models.BooleanField(default=False, verbose_name="Profil domyslny")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'name']
        verbose_name = "Profil wizualny (branding)"
        verbose_name_plural = "Profile wizualne (branding)"

    def __str__(self):
        marker = " (domyslny)" if self.is_default else ""
        return f"{self.name}{marker}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            BrandingProfile.objects.exclude(pk=self.pk).update(is_default=False)

    @classmethod
    def get_default(cls):
        """Zwraca domyslny profil brandingu. Jesli zaden nie jest oznaczony
        jako domyslny, zwraca pierwszy dostepny, albo None jesli nie ma
        zadnego profilu w bazie (uzywane w Etapie 4 przy generowaniu PDF)."""
        profile = cls.objects.filter(is_default=True).first()
        if profile:
            return profile
        return cls.objects.first()
