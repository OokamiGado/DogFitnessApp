from django.contrib import admin
from .models import TrainingSession, Booking, PendingBookingRequest


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    fields = ['dog', 'status', 'linked_plan', 'notes']


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'date', 'start_time', 'end_time', 'capacity', 'status', 'is_public']
    list_filter = ['status', 'is_public', 'date']
    search_fields = ['title', 'location']
    inlines = [BookingInline]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['dog', 'session', 'status', 'linked_plan']
    list_filter = ['status']
    search_fields = ['dog__name']


@admin.register(PendingBookingRequest)
class PendingBookingRequestAdmin(admin.ModelAdmin):
    list_display = ['submitted_name', 'dog_name', 'session', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['submitted_name', 'submitted_phone', 'dog_name']
    readonly_fields = ['ip_address', 'created_at']
