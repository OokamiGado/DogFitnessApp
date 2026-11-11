from django.contrib import admin
from .models import PricingPlan, Payment


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('owner', 'amount', 'payment_date', 'method', 'status', 'created_by')
    list_filter = ('status', 'method', 'payment_date')
    search_fields = ('owner__first_name', 'owner__last_name', 'description')
    date_hierarchy = 'payment_date'
