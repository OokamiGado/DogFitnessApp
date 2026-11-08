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

    # Zestawy cwiczen
    path('plans/<int:plan_pk>/sets/add/', views.set_create, name='set_create'),
    path('sets/<int:pk>/edit/', views.set_update, name='set_update'),
    path('sets/<int:pk>/delete/', views.set_delete, name='set_delete'),
    path('sets/<int:pk>/move-up/', views.set_move_up, name='set_move_up'),
    path('sets/<int:pk>/move-down/', views.set_move_down, name='set_move_down'),

    # Cwiczenia w zestawach
    path('sets/<int:set_pk>/exercises/select/', views.plan_exercise_select, name='plan_exercise_select'),
    path('sets/<int:set_pk>/exercises/add/<int:exercise_pk>/', views.plan_exercise_add, name='plan_exercise_add'),
    path('plan-exercises/<int:pk>/edit/', views.plan_exercise_update, name='plan_exercise_update'),
    path('plan-exercises/<int:pk>/delete/', views.plan_exercise_delete, name='plan_exercise_delete'),
    path('plan-exercises/<int:pk>/move-up/', views.plan_exercise_move_up, name='plan_exercise_move_up'),
    path('plan-exercises/<int:pk>/move-down/', views.plan_exercise_move_down, name='plan_exercise_move_down'),
]
