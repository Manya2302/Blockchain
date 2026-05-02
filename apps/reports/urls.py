from django.urls import path
from django.shortcuts import redirect
from . import views
app_name = 'reports'
urlpatterns = [
    path('', lambda r: redirect('evidence:list'), name='home'),
    path('evidence/<int:pk>/pdf/', views.download_report, name='evidence_pdf'),
]
