# Migracja NAPISANA RECZNIE (nie przez makemigrations) - Django nie
# wspiera bezposredniego AlterField z plain ManyToManyField na M2M
# z through= w jednym kroku. Dzielimy to na: utworzenie modelu
# ExerciseEquipment -> skopiowanie istniejacych danych (kazde
# dotychczasowe przypisanie sprzetu dostaje quantity=1, trener moze
# to skorygowac pozniej recznie) -> usuniecie starego pola ->
# dodanie nowego pola z through=.

import django.db.models.deletion
from django.db import migrations, models


def copy_equipment_to_through_model(apps, schema_editor):
    """Kopiuje istniejace przypisania Exercise<->Equipment do nowego
    modelu ExerciseEquipment, z domyslna iloscia=1 dla kazdego."""
    Exercise = apps.get_model('exercises', 'Exercise')
    ExerciseEquipment = apps.get_model('exercises', 'ExerciseEquipment')

    for exercise in Exercise.objects.all():
        for equipment in exercise.equipment.all():
            ExerciseEquipment.objects.get_or_create(
                exercise=exercise, equipment=equipment,
                defaults={'quantity': 1}
            )


def copy_through_model_back_to_equipment(apps, schema_editor):
    """Operacja odwrotna (na wypadek rollbacku migracji) - odtwarza
    plain M2M z danych ExerciseEquipment (ignorujac quantity)."""
    ExerciseEquipment = apps.get_model('exercises', 'ExerciseEquipment')
    for item in ExerciseEquipment.objects.all():
        item.exercise.equipment.add(item.equipment)


class Migration(migrations.Migration):

    dependencies = [
        ("exercises", "0005_exercise_goal"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExerciseEquipment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "quantity",
                    models.PositiveSmallIntegerField(default=1, verbose_name="Ilosc"),
                ),
                (
                    "equipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exercise_items",
                        to="exercises.equipment",
                    ),
                ),
                (
                    "exercise",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="equipment_items",
                        to="exercises.exercise",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sprzet do cwiczenia",
                "verbose_name_plural": "Sprzet do cwiczenia",
                "ordering": ["equipment__name"],
                "unique_together": {("exercise", "equipment")},
            },
        ),
        migrations.RunPython(
            copy_equipment_to_through_model,
            copy_through_model_back_to_equipment,
        ),
        migrations.RemoveField(
            model_name="exercise",
            name="equipment",
        ),
        migrations.AddField(
            model_name="exercise",
            name="equipment",
            field=models.ManyToManyField(
                blank=True,
                related_name="exercises",
                through="exercises.ExerciseEquipment",
                to="exercises.equipment",
                verbose_name="Potrzebny sprzet",
            ),
        ),
    ]
