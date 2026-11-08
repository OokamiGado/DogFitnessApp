from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator

from clients.models import Dog
from exercises.models import Exercise, MuscleGroup
from .models import TrainingPlan, ExerciseSet, PlanExercise, PlanTemplate
from .forms import TrainingPlanForm, ExerciseSetForm, PlanExerciseForm

EXERCISES_PER_PAGE = 20


# ============ TRAINING PLAN ============

@login_required
def plan_list(request, dog_pk):
    dog = get_object_or_404(Dog, pk=dog_pk)
    plans = dog.training_plans.filter(is_active=True)
    templates = PlanTemplate.objects.filter(is_active=True)
    return render(request, 'plans/plan_list.html', {
        'dog': dog,
        'plans': plans,
        'templates': templates,
    })


@login_required
def plan_create_blank(request, dog_pk):
    dog = get_object_or_404(Dog, pk=dog_pk)
    if request.method == 'POST':
        form = TrainingPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.dog = dog
            plan.save()
            messages.success(request, f'Plan "{plan.name}" zostal utworzony.')
            return redirect('plan_detail', pk=plan.pk)
    else:
        form = TrainingPlanForm()
    return render(request, 'plans/plan_form.html', {
        'form': form,
        'dog': dog,
        'title': 'Nowy plan od zera',
    })


@login_required
def plan_create_from_template(request, dog_pk):
    dog = get_object_or_404(Dog, pk=dog_pk)
    templates = PlanTemplate.objects.filter(is_active=True)

    if request.method == 'POST':
        template_id = request.POST.get('template')
        template = get_object_or_404(PlanTemplate, pk=template_id, is_active=True)

        plan = TrainingPlan.objects.create(
            dog=dog,
            name=f"{template.name} - {dog.name}",
            status=TrainingPlan.STATUS_DRAFT,
            training_goal=template.training_goal,
            safety_rules=template.safety_rules,
            created_from_template=template,
        )

        for t_set in template.exercise_sets.all():
            new_set = ExerciseSet.objects.create(
                plan=plan,
                name=t_set.name,
                frequency_min=t_set.frequency_min,
                frequency_max=t_set.frequency_max,
                frequency_period=t_set.frequency_period,
                order=t_set.order,
            )
            for t_pe in t_set.plan_exercises.all():
                PlanExercise.objects.create(
                    exercise_set=new_set,
                    exercise=t_pe.exercise,
                    order=t_pe.order,
                    goal_text=t_pe.goal_text,
                    execution_text=t_pe.execution_text,
                    reps_text=t_pe.reps_text,
                    notes_text=t_pe.notes_text,
                )

        messages.success(request, f'Plan zostal utworzony na podstawie szablonu "{template.name}". Mozesz go teraz zmodyfikowac.')
        return redirect('plan_detail', pk=plan.pk)

    return render(request, 'plans/plan_create_from_template.html', {
        'dog': dog,
        'templates': templates,
    })


@login_required
def plan_detail(request, pk):
    plan = get_object_or_404(TrainingPlan, pk=pk)
    conflicts = plan.get_conflicts()
    conflict_pks = {pe.pk for pe, _tags in conflicts}
    return render(request, 'plans/plan_detail.html', {
        'plan': plan,
        'dog': plan.dog,
        'conflicts': conflicts,
        'conflict_pks': conflict_pks,
    })


@login_required
def plan_update(request, pk):
    plan = get_object_or_404(TrainingPlan, pk=pk)
    if request.method == 'POST':
        form = TrainingPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, 'Plan zostal zaktualizowany.')
            return redirect('plan_detail', pk=plan.pk)
    else:
        form = TrainingPlanForm(instance=plan)
    return render(request, 'plans/plan_form.html', {
        'form': form,
        'dog': plan.dog,
        'plan': plan,
        'title': 'Edytuj plan',
    })


@login_required
def plan_delete(request, pk):
    plan = get_object_or_404(TrainingPlan, pk=pk)
    if request.method == 'POST':
        plan.is_active = False
        plan.save()
        messages.success(request, 'Plan zostal przeniesiony do archiwum.')
        return redirect('plan_list', dog_pk=plan.dog.pk)
    return render(request, 'plans/plan_confirm_delete.html', {'plan': plan})


@login_required
def plan_archived_list(request, dog_pk):
    dog = get_object_or_404(Dog, pk=dog_pk)
    plans = dog.training_plans.filter(is_active=False).order_by('-updated_at')
    return render(request, 'plans/plan_archived_list.html', {'dog': dog, 'plans': plans})


@login_required
def plan_restore(request, pk):
    plan = get_object_or_404(TrainingPlan, pk=pk, is_active=False)
    if request.method == 'POST':
        plan.is_active = True
        plan.save()
        messages.success(request, 'Plan zostal przywrocony.')
    return redirect('plan_archived_list', dog_pk=plan.dog.pk)


@login_required
def plan_delete_permanent(request, pk):
    plan = get_object_or_404(TrainingPlan, pk=pk, is_active=False)
    dog_pk = plan.dog.pk
    if request.method == 'POST':
        plan.delete()
        messages.success(request, 'Plan zostal usuniety na zawsze.')
    return redirect('plan_archived_list', dog_pk=dog_pk)


# ============ EXERCISE SET ============

@login_required
def set_create(request, plan_pk):
    plan = get_object_or_404(TrainingPlan, pk=plan_pk)
    if request.method == 'POST':
        form = ExerciseSetForm(request.POST)
        if form.is_valid():
            exercise_set = form.save(commit=False)
            exercise_set.plan = plan
            exercise_set.order = plan.exercise_sets.count()
            exercise_set.save()
            messages.success(request, f'Zestaw "{exercise_set.name}" zostal dodany.')
            return redirect('plan_detail', pk=plan.pk)
    else:
        default_name = f"Zestaw {plan.exercise_sets.count() + 1}"
        form = ExerciseSetForm(initial={'name': default_name})
    return render(request, 'plans/set_form.html', {
        'form': form,
        'plan': plan,
        'title': 'Dodaj zestaw cwiczen',
    })


@login_required
def set_update(request, pk):
    exercise_set = get_object_or_404(ExerciseSet, pk=pk)
    if request.method == 'POST':
        form = ExerciseSetForm(request.POST, instance=exercise_set)
        if form.is_valid():
            form.save()
            messages.success(request, 'Zestaw zostal zaktualizowany.')
            return redirect('plan_detail', pk=exercise_set.plan.pk)
    else:
        form = ExerciseSetForm(instance=exercise_set)
    return render(request, 'plans/set_form.html', {
        'form': form,
        'plan': exercise_set.plan,
        'exercise_set': exercise_set,
        'title': 'Edytuj zestaw',
    })


@login_required
def set_delete(request, pk):
    exercise_set = get_object_or_404(ExerciseSet, pk=pk)
    plan_pk = exercise_set.plan.pk
    if request.method == 'POST':
        exercise_set.delete()
        messages.success(request, 'Zestaw zostal usuniety.')
        return redirect('plan_detail', pk=plan_pk)
    return render(request, 'plans/set_confirm_delete.html', {'exercise_set': exercise_set})


@login_required
def set_move_up(request, pk):
    exercise_set = get_object_or_404(ExerciseSet, pk=pk)
    if request.method == 'POST':
        siblings = list(exercise_set.plan.exercise_sets.order_by('order', 'pk'))
        idx = siblings.index(exercise_set)
        if idx > 0:
            prev_set = siblings[idx - 1]
            exercise_set.order, prev_set.order = prev_set.order, exercise_set.order
            exercise_set.save()
            prev_set.save()
    return redirect('plan_detail', pk=exercise_set.plan.pk)


@login_required
def set_move_down(request, pk):
    exercise_set = get_object_or_404(ExerciseSet, pk=pk)
    if request.method == 'POST':
        siblings = list(exercise_set.plan.exercise_sets.order_by('order', 'pk'))
        idx = siblings.index(exercise_set)
        if idx < len(siblings) - 1:
            next_set = siblings[idx + 1]
            exercise_set.order, next_set.order = next_set.order, exercise_set.order
            exercise_set.save()
            next_set.save()
    return redirect('plan_detail', pk=exercise_set.plan.pk)


# ============ PLAN EXERCISE (wybor z katalogu + edycja) ============

@login_required
def plan_exercise_select(request, set_pk):
    exercise_set = get_object_or_404(ExerciseSet, pk=set_pk)
    dog = exercise_set.plan.dog

    exercises = Exercise.objects.filter(is_active=True).prefetch_related(
        'muscle_groups', 'contraindication_tags'
    )

    search_query = request.GET.get('q', '').strip()
    muscle_group_filter = request.GET.get('muscle_group', '').strip()

    if search_query:
        exercises = exercises.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query) |
            Q(variant_name__icontains=search_query)
        )
    if muscle_group_filter:
        exercises = exercises.filter(muscle_groups__id=muscle_group_filter)

    exercises = exercises.distinct().order_by('name')

    paginator = Paginator(exercises, EXERCISES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    dog_tag_ids = set(dog.health_tags.values_list('pk', flat=True))
    for ex in page_obj:
        ex_tag_ids = set(ex.contraindication_tags.values_list('pk', flat=True))
        ex.shared_tag_names = [
            t.name for t in ex.contraindication_tags.all() if t.pk in dog_tag_ids
        ]

    return render(request, 'plans/plan_exercise_select.html', {
        'exercise_set': exercise_set,
        'dog': dog,
        'page_obj': page_obj,
        'search_query': search_query,
        'muscle_group_filter': muscle_group_filter,
        'muscle_groups': MuscleGroup.objects.all(),
    })


@login_required
def plan_exercise_add(request, set_pk, exercise_pk):
    exercise_set = get_object_or_404(ExerciseSet, pk=set_pk)
    exercise = get_object_or_404(Exercise, pk=exercise_pk)
    dog = exercise_set.plan.dog

    if request.method == 'POST':
        shared_tags = dog.get_shared_tags(exercise)

        plan_exercise = PlanExercise.objects.create(
            exercise_set=exercise_set,
            exercise=exercise,
            order=exercise_set.plan_exercises.count(),
            goal_text='',
            execution_text=exercise.description,
            reps_text='',
            notes_text='',
        )

        if shared_tags:
            tag_names = ', '.join(t.name for t in shared_tags)
            messages.warning(
                request,
                f'Uwaga: cwiczenie "{exercise.name}" ma tagi wspolne z profilem zdrowotnym '
                f'{dog.name}: {tag_names}. Sprawdz, czy to bezpieczne dla tego psa.'
            )
        messages.success(request, f'Cwiczenie "{exercise.name}" zostalo dodane do zestawu.')
        return redirect('plan_exercise_update', pk=plan_exercise.pk)

    return redirect('plan_exercise_select', set_pk=exercise_set.pk)


@login_required
def plan_exercise_update(request, pk):
    plan_exercise = get_object_or_404(PlanExercise, pk=pk)
    plan = plan_exercise.exercise_set.plan
    dog = plan.dog
    shared_tags = dog.get_shared_tags(plan_exercise.exercise)

    if request.method == 'POST':
        form = PlanExerciseForm(request.POST, instance=plan_exercise)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cwiczenie w planie zostalo zaktualizowane.')
            return redirect('plan_detail', pk=plan.pk)
    else:
        form = PlanExerciseForm(instance=plan_exercise)

    return render(request, 'plans/plan_exercise_form.html', {
        'form': form,
        'plan_exercise': plan_exercise,
        'plan': plan,
        'shared_tags': shared_tags,
    })


@login_required
def plan_exercise_delete(request, pk):
    plan_exercise = get_object_or_404(PlanExercise, pk=pk)
    plan_pk = plan_exercise.exercise_set.plan.pk
    if request.method == 'POST':
        plan_exercise.delete()
        messages.success(request, 'Cwiczenie zostalo usuniete z zestawu.')
    return redirect('plan_detail', pk=plan_pk)


@login_required
def plan_exercise_move_up(request, pk):
    plan_exercise = get_object_or_404(PlanExercise, pk=pk)
    if request.method == 'POST':
        siblings = list(plan_exercise.exercise_set.plan_exercises.order_by('order', 'pk'))
        idx = siblings.index(plan_exercise)
        if idx > 0:
            prev_pe = siblings[idx - 1]
            plan_exercise.order, prev_pe.order = prev_pe.order, plan_exercise.order
            plan_exercise.save()
            prev_pe.save()
    return redirect('plan_detail', pk=plan_exercise.exercise_set.plan.pk)


@login_required
def plan_exercise_move_down(request, pk):
    plan_exercise = get_object_or_404(PlanExercise, pk=pk)
    if request.method == 'POST':
        siblings = list(plan_exercise.exercise_set.plan_exercises.order_by('order', 'pk'))
        idx = siblings.index(plan_exercise)
        if idx < len(siblings) - 1:
            next_pe = siblings[idx + 1]
            plan_exercise.order, next_pe.order = next_pe.order, plan_exercise.order
            plan_exercise.save()
            next_pe.save()
    return redirect('plan_detail', pk=plan_exercise.exercise_set.plan.pk)
