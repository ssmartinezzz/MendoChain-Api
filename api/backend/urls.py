from django.urls import path
from .views import *


urlpatterns = [
    path('hello_world', hello_world),
    path('wine/<int:pk>', WineApiView.as_view(), name='wine_detail_api'),
    path('wine', WineList.as_view(), name='wine_api'),
    path('transaction/<int:pk>', TransactionApiView.as_view(), name='transaction_block'),
    path('transaction', TransactionList.as_view()),
]
