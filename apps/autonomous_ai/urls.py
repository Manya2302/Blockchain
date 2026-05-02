from django.urls import path
from . import views
app_name = "autonomous_ai"
urlpatterns = [
    path('', views.investigation_dashboard, name="dashboard"),
    path('launch/', views.launch_investigation, name="launch"),
    path('<uuid:inv_id>/', views.investigation_detail, name="detail"),
]