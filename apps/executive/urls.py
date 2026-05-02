from django.urls import path
from . import views
app_name = 'executive'
urlpatterns = [
    path('', views.executive_dashboard, name='dashboard'),
]