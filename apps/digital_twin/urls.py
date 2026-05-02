from django.urls import path
from . import views
app_name = "digital_twin"
urlpatterns = [
    path('', views.twin_dashboard, name="dashboard"),
    path('create/', views.create_twin, name="create"),
    path('<uuid:twin_id>/simulate/', views.run_simulation, name="run_sim"),
    path('sim/<int:sim_id>/', views.sim_detail, name="sim_detail"),
]