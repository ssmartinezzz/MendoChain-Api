from django.urls import path
from .views import *


urlpatterns = [
    path('hello_world', hello_world),
    path('wine/<int:pk>', wine_detail_api, name='wine_detail_api'),
    path('wine', wine_api_view, name= 'wine_api'),
    path('transaction/<int:pk>', TransactionRetrieveUpdateDestroy.as_view()),
    path('transaction', TransactionList.as_view()),
]
