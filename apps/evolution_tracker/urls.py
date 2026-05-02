from django.urls import path
from . import views

app_name = 'evolution'

urlpatterns = [
    path('',                              views.tracker_dashboard, name='dashboard'),
    path('compare/<int:evidence_id>/',    views.compare_versions,  name='compare'),
    path('timeline/<int:evidence_id>/',   views.version_timeline,  name='timeline'),
    path('ai-analyze/<int:evidence_id>/', views.run_ai_analysis,   name='ai_analyze'),
    path('ai/<int:analysis_id>/',         views.ai_analysis_detail, name='ai_detail'),
]
