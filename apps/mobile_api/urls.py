from django.urls import path
from . import views
app_name = 'mobile_api'
urlpatterns = [
    path('docs/', views.mobile_api_docs, name='docs'),
    path('login/', views.mobile_login, name='login'),
    path('evidence/', views.mobile_evidence_list, name='evidence_list'),
    path('evidence/upload/', views.mobile_evidence_upload, name='evidence_upload'),
    path('verify-qr/', views.mobile_verify_qr, name='verify_qr'),
    path('stats/', views.mobile_dashboard_stats, name='stats'),
]