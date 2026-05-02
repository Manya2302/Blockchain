from django.urls import path
from . import views
app_name = "threat_sharing"
urlpatterns = [
    path('', views.threat_hub, name="hub"),
    path('contribute/', views.contribute_signature, name="contribute"),
]