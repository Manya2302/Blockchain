from django.urls import path
from . import views
app_name = "global_intel"
urlpatterns = [
    path('', views.global_map, name="map"),
    path('translate/', views.translate_evidence, name="translate"),
    path('translate/<int:evidence_id>/', views.translate_evidence, name="translate_evidence"),
    path('api/events/', views.geo_events_api, name="events_api"),
]