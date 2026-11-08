from django.urls import path
from . import views

urlpatterns = [
    path('clients/', views.owner_list, name='owner_list'),
    path('clients/add/', views.owner_create, name='owner_create'),
    path('clients/export/', views.owner_export_csv, name='owner_export_csv'),
    path('clients/archived/', views.owner_archived_list, name='owner_archived_list'),
    path('clients/<int:pk>/', views.owner_detail, name='owner_detail'),
    path('clients/<int:pk>/edit/', views.owner_update, name='owner_update'),
    path('clients/<int:pk>/delete/', views.owner_delete, name='owner_delete'),
    path('clients/<int:pk>/restore/', views.owner_restore, name='owner_restore'),
    path('clients/<int:pk>/delete-permanent/', views.owner_delete_permanent, name='owner_delete_permanent'),
    path('clients/<int:owner_pk>/dogs/add/', views.dog_create, name='dog_create_for_owner'),

    path('dogs/', views.dog_list, name='dog_list'),
    path('dogs/add/', views.dog_create, name='dog_create'),
    path('dogs/export/', views.dog_export_csv, name='dog_export_csv'),
    path('dogs/archived/', views.dog_archived_list, name='dog_archived_list'),
    path('dogs/<int:pk>/', views.dog_detail, name='dog_detail'),
    path('dogs/<int:pk>/edit/', views.dog_update, name='dog_update'),
    path('dogs/<int:pk>/delete/', views.dog_delete, name='dog_delete'),
    path('dogs/<int:pk>/restore/', views.dog_restore, name='dog_restore'),
    path('dogs/<int:pk>/delete-permanent/', views.dog_delete_permanent, name='dog_delete_permanent'),
    path('dogs/<int:pk>/toggle-status/', views.dog_toggle_training_status, name='dog_toggle_training_status'),
    path('dogs/<int:pk>/pdf/', views.dog_pdf, name='dog_pdf'),

    path('audit-log/', views.audit_log_list, name='audit_log_list'),
]
