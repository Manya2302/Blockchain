from django.urls import path
from . import views
app_name = "legal_ai"
urlpatterns = [
    path('', views.legal_dashboard, name="dashboard"),
    path('generate/', views.generate_document, name="generate"),
    path('generate/<uuid:investigation_id>/', views.generate_document, name="generate_from_inv"),
    path('<uuid:doc_id>/', views.doc_detail, name="doc_detail"),
    path('<uuid:doc_id>/approve/', views.approve_document, name="approve"),
]