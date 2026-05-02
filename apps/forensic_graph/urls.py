from django.urls import path
from . import views
app_name = 'graph'
urlpatterns = [
    path('',                         views.graph_dashboard, name='dashboard'),
    path('data/<int:evidence_id>/',  views.graph_data_api,  name='data'),
]
