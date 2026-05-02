from django.urls import path
from . import views
app_name = 'federated_ai'
urlpatterns = [
    path('', views.federated_dashboard, name='dashboard'),
]