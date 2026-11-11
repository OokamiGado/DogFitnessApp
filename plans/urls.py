from django.urls import path
from . import views

urlpatterns = [
    # Plany (zagniezdzone pod psem)
    path('dogs/<int:dog_pk>/plans/', views.plan_list, name='plan_list'),
    path('dogs/<int:dog_pk>/plans/add/', views.plan_create_blank, name='plan_create_blank'),
    path('dogs/<int:dog_pk>/plans/add-from-template/', views.plan_create_from_template, name='plan_create_from_template'),
    path('dogs/<int:dog_pk>/plans/archived/', views.plan_archived_list, name='plan_archived_list'),

    path('plans/<int:pk>/', views.plan_detail, name='plan_detail'),
    path('plans/<int:pk>/edit/', views.plan_update, name='plan_update'),
    path('plans/<int:pk>/delete/', views.plan_delete, name='plan_delete'),
    path('plans/<int:pk>/restore/', views.plan_restore, name='plan_restore'),
    path('plans/<int:pk>/delete-permanent/', views.plan_delete_permanent, name='plan_delete_permanent'),

    # Zestawy cwiczen (plan konkretnego psa)
    path('plans/<int:plan_pk>/sets/add/', views.set_create, name='set_create'),
    path('sets/<int:pk>/edit/', views.set_update, name='set_update'),
    path('sets/<int:pk>/delete/', views.set_delete, name='set_delete'),
    path('sets/<int:pk>/move-up/', views.set_move_up, name='set_move_up'),
    path('sets/<int:pk>/move-down/', views.set_move_down, name='set_move_down'),

    # Cwiczenia w zestawach (plan konkretnego psa)
    path('sets/<int:set_pk>/exercises/select/', views.plan_exercise_select, name='plan_exercise_select'),
    path('sets/<int:set_pk>/exercises/add/<int:exercise_pk>/', views.plan_exercise_add, name='plan_exercise_add'),
    path('plan-exercises/<int:pk>/edit/', views.plan_exercise_update, name='plan_exercise_update'),
    path('plan-exercises/<int:pk>/delete/', views.plan_exercise_delete, name='plan_exercise_delete'),
    path('plan-exercises/<int:pk>/move-up/', views.plan_exercise_move_up, name='plan_exercise_move_up'),
    path('plan-exercises/<int:pk>/move-down/', views.plan_exercise_move_down, name='plan_exercise_move_down'),

    # ============ SZABLONY PLANOW (Etap 2) ============
    path('templates/', views.template_list, name='template_list'),
    path('templates/add/', views.template_create, name='template_create'),
    path('templates/archived/', views.template_archived_list, name='template_archived_list'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
    path('templates/<int:pk>/edit/', views.template_update, name='template_update'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:pk>/restore/', views.template_restore, name='template_restore'),
    path('templates/<int:pk>/delete-permanent/', views.template_delete_permanent, name='template_delete_permanent'),

    # Zestawy cwiczen (szablon)
    path('templates/<int:template_pk>/sets/add/', views.template_set_create, name='template_set_create'),
    path('template-sets/<int:pk>/edit/', views.template_set_update, name='template_set_update'),
    path('template-sets/<int:pk>/delete/', views.template_set_delete, name='template_set_delete'),
    path('template-sets/<int:pk>/move-up/', views.template_set_move_up, name='template_set_move_up'),
    path('template-sets/<int:pk>/move-down/', views.template_set_move_down, name='template_set_move_down'),

    # Cwiczenia w zestawach (szablon)
    path('template-sets/<int:set_pk>/exercises/select/', views.template_exercise_select, name='template_exercise_select'),
    path('template-sets/<int:set_pk>/exercises/add/<int:exercise_pk>/', views.template_exercise_add, name='template_exercise_add'),
    path('template-plan-exercises/<int:pk>/edit/', views.template_exercise_update, name='template_exercise_update'),
    path('template-plan-exercises/<int:pk>/delete/', views.template_exercise_delete, name='template_exercise_delete'),
    path('template-plan-exercises/<int:pk>/move-up/', views.template_exercise_move_up, name='template_exercise_move_up'),
    path('template-plan-exercises/<int:pk>/move-down/', views.template_exercise_move_down, name='template_exercise_move_down'),
    # ============ BRANDING (Etap 3) ============
    path('branding/', views.branding_list, name='branding_list'),
    path('branding/add/', views.branding_create, name='branding_create'),
    path('branding/<int:pk>/edit/', views.branding_update, name='branding_update'),
    path('branding/<int:pk>/delete/', views.branding_delete, name='branding_delete'),
    path('branding/<int:pk>/set-default/', views.branding_set_default, name='branding_set_default'),
    # ============ GENEROWANIE DOKUMENTOW (Etap 4) ============
    path('plans/<int:pk>/download/detailed-pdf/', views.plan_download_detailed_pdf, name='plan_download_detailed_pdf'),
    path('plans/<int:pk>/download/fiszka-pdf/', views.plan_download_fiszka_pdf, name='plan_download_fiszka_pdf'),
    path('plans/<int:pk>/download/detailed-docx/', views.plan_download_detailed_docx, name='plan_download_detailed_docx'),
    path('plans/<int:pk>/download/fiszka-docx/', views.plan_download_fiszka_docx, name='plan_download_fiszka_docx'),
]
