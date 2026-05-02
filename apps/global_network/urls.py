from django.urls import path
from . import views
app_name = "global_network"
urlpatterns = [
    path('', views.network_dashboard, name="dashboard"),
    path('nodes/<uuid:node_id>/', views.node_detail, name="node_detail"),
    path('register/', views.register_node, name="register_node"),
    path('transfer/<int:evidence_id>/', views.initiate_transfer, name="transfer"),
    path('api/', views.network_api, name="api"),
]