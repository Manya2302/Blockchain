from django.urls import path
from . import views
app_name = "dao_governance"
urlpatterns = [
    path('', views.dao_dashboard, name="dashboard"),
    path('proposal/<uuid:proposal_id>/', views.proposal_detail, name="proposal"),
    path('proposal/<uuid:proposal_id>/vote/', views.cast_vote, name="vote"),
    path('create/', views.create_proposal, name="create"),
]