from django.urls import path
from .views import *


urlpatterns = [
    path('hello_world', hello_world),
    path('wine/<int:pk>', WineRetrieveUpdateDestroy.as_view()),
    path('wine', WineList.as_view()),
    path('transaction/<int:pk>', TransactionRetrieveUpdateDestroy.as_view()),
    path('transaction', TransactionList.as_view()),
]
