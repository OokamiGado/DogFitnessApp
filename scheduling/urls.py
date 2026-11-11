from django.urls import path
from . import views

urlpatterns = [
    # Terminy
    path('scheduling/', views.session_list, name='session_list'),
    path('scheduling/calendar/', views.session_calendar, name='session_calendar'),
    path('scheduling/calendar/feed/', views.session_calendar_feed, name='session_calendar_feed'),
    path('scheduling/sessions/add/', views.session_create, name='session_create'),
    path('scheduling/sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('scheduling/sessions/<int:pk>/edit/', views.session_update, name='session_update'),
    path('scheduling/sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),
    path('scheduling/sessions/<int:pk>/duplicate/', views.session_duplicate, name='session_duplicate'),

    # Rezerwacje
    path('scheduling/sessions/<int:session_pk>/bookings/add-existing/', views.booking_add_existing, name='booking_add_existing'),
    path('scheduling/sessions/<int:session_pk>/bookings/add-new/', views.booking_add_new_client, name='booking_add_new_client'),
    path('scheduling/bookings/<int:pk>/status/<str:new_status>/', views.booking_set_status, name='booking_set_status'),
    path('scheduling/bookings/<int:pk>/link-plan/', views.booking_link_plan, name='booking_link_plan'),
    path('scheduling/bookings/<int:pk>/journal/', views.booking_journal_edit, name='booking_journal_edit'),

    # AJAX
    path('scheduling/ajax/dogs/<int:dog_pk>/plans/', views.ajax_dog_plans, name='ajax_dog_plans'),

    # ============ PUBLICZNE ZAPISY (Etap 4) - BEZ LOGOWANIA ============
    path('scheduling/public/', views.public_session_list, name='public_session_list'),
    path('scheduling/public/<int:pk>/zapisz/', views.public_booking_request, name='public_booking_request'),
    path('scheduling/public/dziekujemy/', views.public_booking_thank_you, name='public_booking_thank_you'),

    # ============ MODERACJA WNIOSKOW (Etap 4) ============
    path('scheduling/pending-requests/', views.pending_request_list, name='pending_request_list'),
    path('scheduling/pending-requests/<int:pk>/approve/', views.pending_request_approve, name='pending_request_approve'),
    path('scheduling/pending-requests/<int:pk>/reject/', views.pending_request_reject, name='pending_request_reject'),
]
