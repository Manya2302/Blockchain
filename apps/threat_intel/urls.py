from django.urls import path
from . import views
app_name = 'threat_intel'
urlpatterns = [
    path('', views.threat_dashboard, name='dashboard'),
    path('attackers/', views.attacker_profiles, name='attackers'),
    path('predict/', views.predict_now, name='predict'),
]