from django.urls import path
from . import views
app_name = 'blockchain'
urlpatterns = [
    path('',                          views.tx_list,     name='tx_list'),
    path('anchor/<int:pk>/',          views.anchor_view, name='anchor'),
]
