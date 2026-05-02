from django.urls import path
from . import views
app_name = 'attack_sim'
urlpatterns = [
    path('',            views.sim_dashboard,    name='dashboard'),
    path('run/',        views.run_simulation,   name='run'),
    path('<int:sim_id>/', views.sim_detail,     name='detail'),
]
