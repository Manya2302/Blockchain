from django.urls import path
from . import views
app_name = 'users'
urlpatterns = [
    path('login/',           views.login_view,          name='login'),
    path('logout/',          views.logout_view,          name='logout'),
    path('register/',        views.register_view,        name='register'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/',      views.verify_otp_view,      name='verify_otp'),
    path('reset-password/',  views.reset_password_view,  name='reset_password'),
    path('change-password/', views.change_password_view, name='change_password'),
]
