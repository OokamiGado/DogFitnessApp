from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
]
