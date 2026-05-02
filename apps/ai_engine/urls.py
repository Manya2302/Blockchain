from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('',                    views.ai_dashboard,      name='dashboard'),
    path('compare/',            views.model_comparison,  name='compare'),
    path('train/',              views.trigger_training,  name='train'),
    path('predict/<int:pk>/',         views.run_prediction, name='predict'),
    path('detail/<int:prediction_id>/', views.prediction_detail, name='detail'),
    path('api/predict/',        views.api_predict,       name='api_predict'),
]
