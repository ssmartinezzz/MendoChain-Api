from django.urls import path
from .views import *


urlpatterns = [
    path('hello_world', hello_world),
    path('wine/<int:pk>', wine_detail_api, name='wine_detail_api'),
    path('wine', wine_api_view, name= 'wine_api'),
    path('transaction/<int:pk>', create_block_transaction, name='transaction_block'),
    path('transaction', TransactionList.as_view()),
]
