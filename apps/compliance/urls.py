from django.urls import path
from . import views
app_name = 'compliance'
urlpatterns = [
    path('', views.compliance_dashboard, name='dashboard'),
    path('start/', views.start_assessment, name='start'),
    path('assessment/<int:assessment_id>/', views.assessment_detail, name='detail'),
]