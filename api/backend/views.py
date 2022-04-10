from .serializers import *
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view


@api_view(['GET'])
def hello_world(request):
    name = "Anonymous" if request.user.is_anonymous else request.user.first_name
    return Response({"hello": f"Welcome to DRF, {name}!"}, 200)


class WineRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Wine.objects.all()
    serializer_class = WineSerializer


class WineList(generics.ListCreateAPIView):
    queryset = Wine.objects.all()
    serializer_class = WineSerializer


class TransactionRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


class TransactionList(generics.ListCreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


