from django.urls import path
from . import views

urlpatterns = [
    path('finance/pricing/', views.pricing_plan_list, name='pricing_plan_list'),
    path('finance/pricing/add/', views.pricing_plan_create, name='pricing_plan_create'),
    path('finance/pricing/<int:pk>/edit/', views.pricing_plan_update, name='pricing_plan_update'),
    path('finance/pricing/<int:pk>/delete/', views.pricing_plan_delete, name='pricing_plan_delete'),
    path('finance/pricing/<int:pk>/toggle/', views.pricing_plan_toggle_active, name='pricing_plan_toggle_active'),

    path('finance/payments/', views.payment_list, name='payment_list'),
    path('finance/payments/add/', views.payment_create, name='payment_create'),
    path('finance/payments/add/owner/<int:owner_pk>/', views.payment_create, name='payment_create_for_owner'),
    path('finance/payments/add/booking/<int:booking_pk>/', views.payment_create, name='payment_create_for_booking'),
    path('finance/payments/<int:pk>/edit/', views.payment_update, name='payment_update'),
    path('finance/payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('finance/payments/<int:pk>/mark-paid/', views.payment_mark_paid, name='payment_mark_paid'),

    path('finance/report/', views.finance_report, name='finance_report'),
    path('finance/report/export/', views.finance_report_export_csv, name='finance_report_export_csv'),
]
