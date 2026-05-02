from django.urls import path
from . import views
app_name = 'billing'
urlpatterns = [
    path('', views.billing_dashboard, name='dashboard'),
    path('admin/', views.admin_billing, name='admin'),
    path('plan/<uuid:org_id>/', views.change_plan, name='change_plan'),
]