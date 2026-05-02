from django.urls import path
from . import views
app_name = "developer_ecosystem"
urlpatterns = [
    path('', views.ecosystem_dashboard, name="dashboard"),
    path('apps/create/', views.create_app, name="create_app"),
    path('docs/', views.api_docs, name="api_docs"),
]