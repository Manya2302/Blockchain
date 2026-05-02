from django.urls import path
from . import profile_views
app_name = 'profile'
urlpatterns = [
    path('',     profile_views.profile_view, name='view'),
    path('edit/', profile_views.profile_edit, name='edit'),
]
