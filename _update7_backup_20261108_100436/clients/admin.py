from django.contrib import admin
from .models import Owner, Dog


class DogInline(admin.TabularInline):
    model = Dog
    extra = 1
    fields = ('name', 'breed', 'birth_date', 'weight_kg', 'is_active')


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('first_name', 'last_name', 'phone', 'email')
    inlines = [DogInline]
    actions = ['make_active', 'make_archived']

    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Przywrocono {updated} wlascicieli.")
    make_active.short_description = "Przywroc zaznaczonych"

    def make_archived(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Zarchiwizowano {updated} wlascicieli.")
    make_archived.short_description = "Zarchiwizuj zaznaczonych"


@admin.register(Dog)
class DogAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'breed', 'is_active', 'created_at')
    list_filter = ('is_active', 'breed')
    search_fields = ('name', 'breed', 'owner__first_name', 'owner__last_name')
