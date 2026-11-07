from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import MuscleGroup, Equipment, Exercise, ExerciseImage
from .forms import MuscleGroupForm, EquipmentForm, ExerciseForm, ExerciseImageUploadForm


# ============ MUSCLE GROUP ============

def muscle_group_list(request):
    muscle_groups = MuscleGroup.objects.all()
    return render(request, 'exercises/muscle_group_list.html', {
        'muscle_groups': muscle_groups
    })


def muscle_group_create(request):
    if request.method == 'POST':
        form = MuscleGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grupa mięśniowa została dodana.')
            return redirect('muscle_group_list')
    else:
        form = MuscleGroupForm()
    return render(request, 'exercises/muscle_group_form.html', {
        'form': form,
        'title': 'Dodaj grupę mięśniową'
    })


def muscle_group_update(request, pk):
    muscle_group = get_object_or_404(MuscleGroup, pk=pk)
    if request.method == 'POST':
        form = MuscleGroupForm(request.POST, instance=muscle_group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grupa mięśniowa została zaktualizowana.')
            return redirect('muscle_group_list')
    else:
        form = MuscleGroupForm(instance=muscle_group)
    return render(request, 'exercises/muscle_group_form.html', {
        'form': form,
        'title': 'Edytuj grupę mięśniową'
    })


def muscle_group_delete(request, pk):
    muscle_group = get_object_or_404(MuscleGroup, pk=pk)
    if request.method == 'POST':
        muscle_group.delete()
        messages.success(request, 'Grupa mięśniowa została usunięta.')
        return redirect('muscle_group_list')
    return render(request, 'exercises/muscle_group_confirm_delete.html', {
        'muscle_group': muscle_group
    })


# ============ EQUIPMENT ============

def equipment_list(request):
    equipment = Equipment.objects.all()
    return render(request, 'exercises/equipment_list.html', {
        'equipment': equipment
    })


def equipment_create(request):
    if request.method == 'POST':
        form = EquipmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sprzęt został dodany.')
            return redirect('equipment_list')
    else:
        form = EquipmentForm()
    return render(request, 'exercises/equipment_form.html', {
        'form': form,
        'title': 'Dodaj sprzęt'
    })


def equipment_update(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        form = EquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sprzęt został zaktualizowany.')
            return redirect('equipment_list')
    else:
        form = EquipmentForm(instance=equipment)
    return render(request, 'exercises/equipment_form.html', {
        'form': form,
        'title': 'Edytuj sprzęt'
    })


def equipment_delete(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        equipment.delete()
        messages.success(request, 'Sprzęt został usunięty.')
        return redirect('equipment_list')
    return render(request, 'exercises/equipment_confirm_delete.html', {
        'equipment': equipment
    })


# ============ EXERCISE ============

def exercise_list(request):
    exercises = Exercise.objects.prefetch_related('muscle_groups', 'equipment', 'images').all()

    search_query = request.GET.get('q', '').strip()
    muscle_group_filter = request.GET.get('muscle_group')
    difficulty_filter = request.GET.get('difficulty')

    if search_query:
        exercises = exercises.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    if muscle_group_filter:
        exercises = exercises.filter(muscle_groups__id=muscle_group_filter)
    if difficulty_filter:
        exercises = exercises.filter(difficulty=difficulty_filter)

    return render(request, 'exercises/exercise_list.html', {
        'exercises': exercises.distinct(),
        'muscle_groups': MuscleGroup.objects.all(),
        'difficulty_choices': Exercise.DIFFICULTY_CHOICES,
        'selected_muscle_group': muscle_group_filter,
        'selected_difficulty': difficulty_filter,
        'search_query': search_query,
    })


def exercise_detail(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk)
    return render(request, 'exercises/exercise_detail.html', {
        'exercise': exercise
    })


def exercise_create(request):
    if request.method == 'POST':
        form = ExerciseForm(request.POST)
        image_form = ExerciseImageUploadForm(request.POST, request.FILES)

        if form.is_valid() and image_form.is_valid():
            exercise = form.save()

            images = request.FILES.getlist('images')
            for img in images:
                ExerciseImage.objects.create(exercise=exercise, image=img)

            messages.success(request, 'Ćwiczenie zostało dodane.')
            return redirect('exercise_detail', pk=exercise.pk)
    else:
        form = ExerciseForm()
        image_form = ExerciseImageUploadForm()

    return render(request, 'exercises/exercise_form.html', {
        'form': form,
        'image_form': image_form,
        'title': 'Dodaj ćwiczenie'
    })


def exercise_update(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk)

    if request.method == 'POST':
        form = ExerciseForm(request.POST, instance=exercise)
        image_form = ExerciseImageUploadForm(request.POST, request.FILES)

        if form.is_valid() and image_form.is_valid():
            form.save()

            images = request.FILES.getlist('images')
            for img in images:
                ExerciseImage.objects.create(exercise=exercise, image=img)

            messages.success(request, 'Ćwiczenie zostało zaktualizowane.')
            return redirect('exercise_detail', pk=exercise.pk)
    else:
        form = ExerciseForm(instance=exercise)
        image_form = ExerciseImageUploadForm()

    return render(request, 'exercises/exercise_form.html', {
        'form': form,
        'image_form': image_form,
        'title': 'Edytuj ćwiczenie',
        'exercise': exercise,
    })


def exercise_delete(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk)
    if request.method == 'POST':
        exercise.delete()
        messages.success(request, 'Ćwiczenie zostało usunięte.')
        return redirect('exercise_list')
    return render(request, 'exercises/exercise_confirm_delete.html', {
        'exercise': exercise
    })


def exercise_image_delete(request, pk):
    """Usunięcie pojedynczego zdjęcia z galerii ćwiczenia"""
    image = get_object_or_404(ExerciseImage, pk=pk)
    exercise_pk = image.exercise.pk
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Zdjęcie zostało usunięte.')
    return redirect('exercise_update', pk=exercise_pk)