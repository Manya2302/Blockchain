from django.urls import path
from . import views
app_name = 'analysis'
urlpatterns = [
    path('anomalies/',                 views.anomaly_list,    name='anomaly_list'),
    path('anomalies/<int:pk>/resolve/',views.resolve_anomaly, name='resolve'),
    path('evidence/<int:pk>/rescan/',  views.rescan_evidence, name='rescan'),
]
