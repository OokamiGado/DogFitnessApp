import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Case, When, IntegerField
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import MuscleGroup, Equipment, Exercise, ExerciseImage
from .forms import MuscleGroupForm, EquipmentForm, ExerciseForm, ExerciseImageUploadForm

EXERCISES_PER_PAGE = 25

SORT_OPTIONS = [
    ('newest', 'Najnowsze'),
    ('oldest', 'Najstarsze'),
    ('name_asc', 'Nazwa A-Z'),
    ('name_desc', 'Nazwa Z-A'),
    ('difficulty', 'Poziom trudnosci'),
]


# ============ MUSCLE GROUP ============

@login_required
def muscle_group_list(request):
    muscle_groups = MuscleGroup.objects.all()
    return render(request, 'exercises/muscle_group_list.html', {
        'muscle_groups': muscle_groups
    })


@login_required
def muscle_group_create(request):
    if request.method == 'POST':
        form = MuscleGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grupa miesniowa zostala dodana.')
            return redirect('muscle_group_list')
    else:
        form = MuscleGroupForm()
    return render(request, 'exercises/muscle_group_form.html', {
        'form': form,
        'title': 'Dodaj grupe miesniowa'
    })


@login_required
def muscle_group_update(request, pk):
    muscle_group = get_object_or_404(MuscleGroup, pk=pk)
    if request.method == 'POST':
        form = MuscleGroupForm(request.POST, instance=muscle_group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grupa miesniowa zostala zaktualizowana.')
            return redirect('muscle_group_list')
    else:
        form = MuscleGroupForm(instance=muscle_group)
    return render(request, 'exercises/muscle_group_form.html', {
        'form': form,
        'title': 'Edytuj grupe miesniowa'
    })


@login_required
def muscle_group_delete(request, pk):
    muscle_group = get_object_or_404(MuscleGroup, pk=pk)
    if request.method == 'POST':
        muscle_group.delete()
        messages.success(request, 'Grupa miesniowa zostala usunieta.')
        return redirect('muscle_group_list')
    return render(request, 'exercises/muscle_group_confirm_delete.html', {
        'muscle_group': muscle_group
    })


# ============ EQUIPMENT ============

@login_required
def equipment_list(request):
    equipment = Equipment.objects.all()
    return render(request, 'exercises/equipment_list.html', {
        'equipment': equipment
    })


@login_required
def equipment_create(request):
    if request.method == 'POST':
        form = EquipmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sprzet zostal dodany.')
            return redirect('equipment_list')
    else:
        form = EquipmentForm()
    return render(request, 'exercises/equipment_form.html', {
        'form': form,
        'title': 'Dodaj sprzet'
    })


@login_required
def equipment_update(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        form = EquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sprzet zostal zaktualizowany.')
            return redirect('equipment_list')
    else:
        form = EquipmentForm(instance=equipment)
    return render(request, 'exercises/equipment_form.html', {
        'form': form,
        'title': 'Edytuj sprzet'
    })


@login_required
def equipment_delete(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        equipment.delete()
        messages.success(request, 'Sprzet zostal usuniety.')
        return redirect('equipment_list')
    return render(request, 'exercises/equipment_confirm_delete.html', {
        'equipment': equipment
    })


# ============ EXERCISE ============

@login_required
def exercise_list(request):
    exercises = Exercise.objects.filter(
        parent_exercise__isnull=True, is_active=True
    ).prefetch_related('muscle_groups', 'equipment', 'images', 'variants')

    search_query = request.GET.get('q', '').strip()
    muscle_group_filter = request.GET.get('muscle_group')
    difficulty_filter = request.GET.get('difficulty')
    sort = request.GET.get('sort', 'newest')

    if search_query:
        exercises = exercises.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query) |
            Q(variants__name__icontains=search_query) | Q(variants__description__icontains=search_query)
        )

    if muscle_group_filter:
        exercises = exercises.filter(
            Q(muscle_groups__id=muscle_group_filter) | Q(variants__muscle_groups__id=muscle_group_filter)
        )
    if difficulty_filter:
        exercises = exercises.filter(
            Q(difficulty=difficulty_filter) | Q(variants__difficulty=difficulty_filter)
        )

    exercises = exercises.distinct()

    if sort == 'oldest':
        exercises = exercises.order_by('created_at')
    elif sort == 'name_asc':
        exercises = exercises.order_by('name')
    elif sort == 'name_desc':
        exercises = exercises.order_by('-name')
    elif sort == 'difficulty':
        order = Case(
            When(difficulty='easy', then=0),
            When(difficulty='medium', then=1),
            When(difficulty='hard', then=2),
            output_field=IntegerField()
        )
        exercises = exercises.annotate(diff_order=order).order_by('diff_order')
    else:
        exercises = exercises.order_by('-created_at')
        sort = 'newest'

    paginator = Paginator(exercises, EXERCISES_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    querystring = get_copy.urlencode()

    stats_qs = Exercise.objects.filter(is_active=True)
    stats = {
        'total': stats_qs.count(),
        'main': stats_qs.filter(parent_exercise__isnull=True).count(),
        'variants': stats_qs.filter(parent_exercise__isnull=False).count(),
        'easy': stats_qs.filter(difficulty='easy').count(),
        'medium': stats_qs.filter(difficulty='medium').count(),
        'hard': stats_qs.filter(difficulty='hard').count(),
    }

    return render(request, 'exercises/exercise_list.html', {
        'page_obj': page_obj,
        'muscle_groups': MuscleGroup.objects.all(),
        'difficulty_choices': Exercise.DIFFICULTY_CHOICES,
        'sort_options': SORT_OPTIONS,
        'selected_muscle_group': muscle_group_filter,
        'selected_difficulty': difficulty_filter,
        'selected_sort': sort,
        'search_query': search_query,
        'querystring': querystring,
        'stats': stats,
    })


@login_required
def exercise_detail(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk)
    return render(request, 'exercises/exercise_detail.html', {
        'exercise': exercise
    })


def _create_images_with_order(exercise, images):
    """Tworzy obiekty ExerciseImage z poprawna, narastajaca kolejnoscia."""
    start_order = exercise.images.count()
    created = []
    for idx, img in enumerate(images):
        obj = ExerciseImage.objects.create(exercise=exercise, image=img, order=start_order + idx)
        created.append(obj)
    return created


@login_required
def exercise_create(request):
    if request.method == 'POST':
        form = ExerciseForm(request.POST)
        image_form = ExerciseImageUploadForm(request.POST, request.FILES)

        if form.is_valid() and image_form.is_valid():
            exercise = form.save()

            images = request.FILES.getlist('images')
            _create_images_with_order(exercise, images)

            if images and not exercise.images.filter(is_cover=True).exists():
                first_img = exercise.images.order_by('order', 'pk').first()
                if first_img:
                    first_img.is_cover = True
                    first_img.save()

            messages.success(request, 'Cwiczenie zostalo dodane.')
            return redirect('exercise_detail', pk=exercise.pk)
    else:
        form = ExerciseForm()
        image_form = ExerciseImageUploadForm()

    return render(request, 'exercises/exercise_form.html', {
        'form': form,
        'image_form': image_form,
        'title': 'Dodaj cwiczenie'
    })


@login_required
def exercise_update(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk)

    if request.method == 'POST':
        form = ExerciseForm(request.POST, instance=exercise)
        image_form = ExerciseImageUploadForm(request.POST, request.FILES)

        if form.is_valid() and image_form.is_valid():
            form.save()

            images = request.FILES.getlist('images')
            _create_images_with_order(exercise, images)

            cover_id = request.POST.get('cover_image')
            if cover_id:
                exercise.images.update(is_cover=False)
                ExerciseImage.objects.filter(pk=cover_id, exercise=exercise).update(is_cover=True)

            if not exercise.images.filter(is_cover=True).exists():
                first_img = exercise.images.order_by('order', 'pk').first()
                if first_img:
                    first_img.is_cover = True
                    first_img.save()

            messages.success(request, 'Cwiczenie zostalo zaktualizowane.')
            return redirect('exercise_detail', pk=exercise.pk)
    else:
        form = ExerciseForm(instance=exercise)
        image_form = ExerciseImageUploadForm()

    return render(request, 'exercises/exercise_form.html', {
        'form': form,
        'image_form': image_form,
        'title': 'Edytuj cwiczenie',
        'exercise': exercise,
    })


@login_required
def exercise_delete(request, pk):
    """Soft delete - przeniesienie do archiwum"""
    exercise = get_object_or_404(Exercise, pk=pk)
    active_variants_count = exercise.variants.filter(is_active=True).count()

    if request.method == 'POST':
        exercise.is_active = False
        exercise.save()
        messages.success(request, 'Cwiczenie zostalo przeniesione do archiwum.')
        return redirect('exercise_list')

    return render(request, 'exercises/exercise_confirm_delete.html', {
        'exercise': exercise,
        'active_variants_count': active_variants_count,
    })


@login_required
def exercise_duplicate(request, pk):
    original = get_object_or_404(Exercise, pk=pk)

    new_parent = original.parent_exercise if original.parent_exercise else original

    new_exercise = Exercise.objects.create(
        name=f"{original.name} (kopia)",
        description=original.description,
        video_url=original.video_url,
        difficulty=original.difficulty,
        contraindications=original.contraindications,
        parent_exercise=new_parent,
        variant_name=original.variant_name or "Nowy wariant",
        is_active=True,
    )
    new_exercise.muscle_groups.set(original.muscle_groups.all())
    new_exercise.equipment.set(original.equipment.all())

    messages.success(request, 'Cwiczenie zostalo zduplikowane jako wariant. Zdjecia nie zostaly skopiowane - dodaj je osobno.')
    return redirect('exercise_update', pk=new_exercise.pk)


@login_required
def exercise_archived_list(request):
    exercises = Exercise.objects.filter(is_active=False).order_by('-updated_at')
    return render(request, 'exercises/exercise_archived_list.html', {
        'exercises': exercises
    })


@login_required
def exercise_restore(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk, is_active=False)
    if request.method == 'POST':
        exercise.is_active = True
        exercise.save()
        messages.success(request, 'Cwiczenie zostalo przywrocone.')
    return redirect('exercise_archived_list')


@login_required
def exercise_delete_permanent(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk, is_active=False)
    if request.method == 'POST':
        exercise.delete()
        messages.success(request, 'Cwiczenie zostalo usuniete na zawsze.')
    return redirect('exercise_archived_list')


@login_required
def exercise_image_delete(request, pk):
    """Usuniecie pojedynczego zdjecia z galerii cwiczenia"""
    image = get_object_or_404(ExerciseImage, pk=pk)
    exercise_pk = image.exercise.pk
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Zdjecie zostalo usuniete.')
    return redirect('exercise_update', pk=exercise_pk)


@login_required
def exercise_image_reorder(request, pk):
    """Endpoint AJAX do zapisywania nowej kolejnosci zdjec (drag&drop)."""
    exercise = get_object_or_404(Exercise, pk=pk)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Metoda niedozwolona.'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        order_list = payload.get('order', [])
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Nieprawidlowe dane.'}, status=400)

    for idx, image_id in enumerate(order_list):
        ExerciseImage.objects.filter(pk=image_id, exercise=exercise).update(order=idx)

    return JsonResponse({'status': 'ok'})
