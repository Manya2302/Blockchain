from django.urls import path
from . import views
app_name = 'org'
urlpatterns = [
    path('', views.org_list, name='list'),
    path('create/', views.org_create, name='create'),
    path('<slug:slug>/', views.org_detail, name='detail'),
    path('<slug:slug>/invite/', views.org_invite_member, name='invite'),
    path('<slug:slug>/api-key/', views.org_generate_api_key, name='api_key'),
]