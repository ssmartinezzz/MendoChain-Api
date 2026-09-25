from django.urls import path

from api.traceability.interfaces import views

# Paths are kept for compatibility with Mendochain-Web.
urlpatterns = [
    path('hello_world', views.hello_world),
    path('wine', views.WineCollection.as_view(), name='wine_api'),
    path('wine/<int:pk>', views.WineDetail.as_view(), name='wine_detail_api'),
    path('allwine', views.AllWines.as_view(), name='all_wine'),
    path('transaction', views.MovementCollection.as_view(), name='transaction_api'),
    path('transaction/<int:pk>', views.MovementDetail.as_view(), name='transaction_block'),
    path('actors', views.ActorCollection.as_view(), name='actors'),
    path('actors/<int:pk>', views.ActorDetail.as_view(), name='actor_detail'),
    path('admin/members', views.AdminMembers.as_view(), name='admin_members'),
]
