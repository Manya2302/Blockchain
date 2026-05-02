from django.urls import path
from . import audit_views
app_name = 'audit'
urlpatterns = [path('', audit_views.audit_view, name='logs')]
