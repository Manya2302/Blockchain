from django.urls import path
from . import views
app_name = "quantum_crypto"
urlpatterns = [
    path('', views.qcrypto_dashboard, name="dashboard"),
    path('sign/<int:evidence_id>/', views.sign_evidence, name="sign"),
]