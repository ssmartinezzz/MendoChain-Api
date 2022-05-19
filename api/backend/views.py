from .serializers import *
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework import status


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
    queryset = Transaction.objects.filter(visibility=1)
    serializer_class = TransactionSerializer

@api_view(['GET', 'POST'])
def wine_api_view(request):
    if request.method == 'GET':
        wines = Wine.objects.filter(visibility=1)
        wine_serializer = WineSerializer(wines, many=True)
        return Response(wine_serializer.data, status = status.HTTP_200_OK)

    elif request.method == 'POST':
        wine_serializer = WineSerializer (data = request.data)
        if wine_serializer.is_valid():
            wine_serializer.save()
            return Response(wine_serializer.data, status = status.HTTP_201_CREATED)
        return Response(wine_serializer.errors, status = status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT'])
def wine_detail_api(request, pk=None):
    wine = Wine.objects.filter(id=pk).first()
    if wine:
        if request.method == 'GET':
            wine_serializer = WineSerializer(wine)
            return Response(wine_serializer.data, status = status.HTTP_200_OK)
        elif request.method == 'PUT':
            wine_serializer = WineSerializer(wine, data = request.data)
            if wine_serializer.is_valid():
                wine_serializer.save()
                return Response(wine_serializer.data, status = status.HTTP_200_OK)
            return Response(wine_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    return Response({'message':"Wine not found"}, status = status.HTTP_400_BAD_REQUEST)

@api_view(['POST', 'GET'])
def create_block_transaction(request, pk=None):
    transaction_serializer = TransactionSerializer(data=request.data)

    if request.method =='POST':
        if transaction_serializer.is_valid():
            transaction_serializer.save()
            return Response(transaction_serializer.data, status=status.HTTP_201_CREATED)
        return Response(transaction_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'GET':
        transaction = Transaction.objects.filter(id=pk).first()
        transaction_serializer = TransactionSerializer(transaction)
        return Response(transaction_serializer.data, status = status.HTTP_200_OK)








