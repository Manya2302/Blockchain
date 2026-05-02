from django.urls import path
from . import home_views
app_name = 'home'
urlpatterns = [
    path('',         home_views.home_view,    name='landing'),
    path('about/',   home_views.about_view,   name='about'),
    path('contact/', home_views.contact_view, name='contact'),
    path('faq/',     home_views.faq_view,     name='faq'),
]
