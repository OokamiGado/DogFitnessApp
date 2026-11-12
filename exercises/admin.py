from django.contrib import admin
from .models import MuscleGroup, Equipment, Exercise, ExerciseImage, ContraindicationTag, ExerciseEquipment


class ExerciseImageInline(admin.TabularInline):
    model = ExerciseImage
    extra = 1
    max_num = 5
    fields = ('image', 'is_cover', 'order')


class ExerciseEquipmentInline(admin.TabularInline):
    """Sprzet + ilosc dla cwiczenia - M2M z through= nie wspiera
    filter_horizontal, dlatego uzywamy inline (tak jak dla zdjec)."""
    model = ExerciseEquipment
    extra = 1
    fields = ('equipment', 'quantity')


@admin.register(MuscleGroup)
class MuscleGroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ContraindicationTag)
class ContraindicationTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'variant_name', 'parent_exercise', 'difficulty', 'is_active', 'created_at')
    list_filter = ('difficulty', 'is_active', 'muscle_groups', 'contraindication_tags')
    search_fields = ('name', 'description', 'variant_name')
    filter_horizontal = ('muscle_groups', 'contraindication_tags')
    inlines = [ExerciseImageInline, ExerciseEquipmentInline]
    actions = ['make_active', 'make_archived']
    list_per_page = 50
    date_hierarchy = 'created_at'

    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Przywrocono {updated} cwiczen (ustawiono jako aktywne).")
    make_active.short_description = "Przywroc zaznaczone (ustaw jako aktywne)"

    def make_archived(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Zarchiwizowano {updated} cwiczen.")
    make_archived.short_description = "Zarchiwizuj zaznaczone"
