from django.urls import path
from . import views
app_name = 'iot'
urlpatterns = [
    path('', views.iot_dashboard, name='dashboard'),
    path('register/', views.register_device, name='register'),
    path('push/', views.device_push, name='push'),
]