from django.urls import path
from . import views

urlpatterns = [
    # Cwiczenia
    path('', views.exercise_list, name='exercise_list'),
    path('exercises/add/', views.exercise_create, name='exercise_create'),
    path('exercises/archived/', views.exercise_archived_list, name='exercise_archived_list'),
    path('exercises/<int:pk>/', views.exercise_detail, name='exercise_detail'),
    path('exercises/<int:pk>/edit/', views.exercise_update, name='exercise_update'),
    path('exercises/<int:pk>/delete/', views.exercise_delete, name='exercise_delete'),
    path('exercises/<int:pk>/duplicate/', views.exercise_duplicate, name='exercise_duplicate'),
    path('exercises/<int:pk>/restore/', views.exercise_restore, name='exercise_restore'),
    path('exercises/<int:pk>/delete-permanent/', views.exercise_delete_permanent, name='exercise_delete_permanent'),
    path('exercises/<int:pk>/images/reorder/', views.exercise_image_reorder, name='exercise_image_reorder'),
    path('exercises/image/<int:pk>/delete/', views.exercise_image_delete, name='exercise_image_delete'),

    # Grupy miesniowe
    path('muscle-groups/', views.muscle_group_list, name='muscle_group_list'),
    path('muscle-groups/add/', views.muscle_group_create, name='muscle_group_create'),
    path('muscle-groups/<int:pk>/edit/', views.muscle_group_update, name='muscle_group_update'),
    path('muscle-groups/<int:pk>/delete/', views.muscle_group_delete, name='muscle_group_delete'),

    # Sprzet
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/add/', views.equipment_create, name='equipment_create'),
    path('equipment/<int:pk>/edit/', views.equipment_update, name='equipment_update'),
    path('equipment/<int:pk>/delete/', views.equipment_delete, name='equipment_delete'),
]
