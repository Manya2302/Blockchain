from django.urls import path
from . import views
app_name = 'zkp'
urlpatterns = [
    # Core ZKP
    path('', views.zkp_dashboard, name='dashboard'),
    path('create/<int:evidence_id>/', views.create_proof, name='create'),
    path('detail/<str:proof_id>/', views.proof_detail, name='detail'),
    path('verify/<str:proof_id>/', views.public_verify, name='verify'),
    path('api/<str:proof_id>/', views.verify_api, name='api'),
    # Resume Verification
    path('resume/', views.resume_dashboard, name='resume_dashboard'),
    path('resume/submit/', views.submit_credential, name='submit_credential'),
    path('resume/credential/<int:credential_id>/', views.credential_detail, name='credential_detail'),
    path('resume/verify/<int:credential_id>/', views.verify_credential, name='verify_credential'),
    # Admin
    path('issuers/', views.manage_issuers, name='manage_issuers'),
    path('logs/', views.verification_logs, name='verification_logs'),
]