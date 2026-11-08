from django.contrib import admin
from .models import (
    TrainingPlan, ExerciseSet, PlanExercise,
    PlanTemplate, TemplateExerciseSet, TemplatePlanExercise,
    BrandingProfile,
)


class PlanExerciseInline(admin.TabularInline):
    model = PlanExercise
    extra = 1
    fields = ('exercise', 'order', 'goal_text', 'reps_text')


class ExerciseSetInline(admin.TabularInline):
    model = ExerciseSet
    extra = 1
    fields = ('name', 'frequency_min', 'frequency_max', 'frequency_period', 'order')
    show_change_link = True


@admin.register(TrainingPlan)
class TrainingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'dog', 'status', 'is_active', 'created_from_template', 'created_at')
    list_filter = ('status', 'is_active')
    search_fields = ('name', 'dog__name')
    inlines = [ExerciseSetInline]


@admin.register(ExerciseSet)
class ExerciseSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan', 'frequency_min', 'frequency_max', 'frequency_period', 'order')
    inlines = [PlanExerciseInline]


class TemplatePlanExerciseInline(admin.TabularInline):
    model = TemplatePlanExercise
    extra = 1
    fields = ('exercise', 'order', 'goal_text', 'reps_text')


class TemplateExerciseSetInline(admin.TabularInline):
    model = TemplateExerciseSet
    extra = 1
    fields = ('name', 'frequency_min', 'frequency_max', 'frequency_period', 'order')
    show_change_link = True


@admin.register(PlanTemplate)
class PlanTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = [TemplateExerciseSetInline]


@admin.register(TemplateExerciseSet)
class TemplateExerciseSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'order')
    inlines = [TemplatePlanExerciseInline]


@admin.register(BrandingProfile)
class BrandingProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'font_family', 'primary_color', 'updated_at')
    list_filter = ('is_default', 'font_family')
    search_fields = ('name',)
