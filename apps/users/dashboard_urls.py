from django.urls import path
from . import dashboard_views
app_name = 'dashboard'
urlpatterns = [
    path('',                        dashboard_views.home,        name='home'),
    path('admin/',                  dashboard_views.admin_dash,  name='admin'),
    path('users/',                  dashboard_views.user_list,   name='user_list'),
    path('users/<int:uid>/edit/',   dashboard_views.user_edit,   name='user_edit'),
    path('users/<int:uid>/delete/', dashboard_views.user_delete, name='user_delete'),
]
