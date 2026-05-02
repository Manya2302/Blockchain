from django.urls import path
from . import views
app_name = 'soc'
urlpatterns = [
    path('', views.soc_dashboard, name='dashboard'),
    path('alert/<int:alert_id>/', views.alert_detail, name='alert_detail'),
    path('alert/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    path('api/feed/', views.live_feed_api, name='feed_api'),
    path('api/stats/', views.soc_stats_api, name='stats_api'),
]