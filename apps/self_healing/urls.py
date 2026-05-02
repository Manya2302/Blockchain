from django.urls import path
from . import views
app_name = "self_healing"
urlpatterns = [
    path('', views.infra_dashboard, name="dashboard"),
    path('heal/<int:component_id>/', views.trigger_heal, name="heal"),
    path('api/', views.infra_api, name="api"),
]