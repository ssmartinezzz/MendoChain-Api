from .serializers import *
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.pagination import PageNumberPagination

@api_view(['GET'])
def hello_world(request):
    name = "Anonymous" if request.user.is_anonymous else request.user.first_name
    return Response({"hello": f"Welcome to DRF, {name}!"}, 200)

class WineList(generics.ListCreateAPIView):
    queryset = Wine.objects.filter(visibility=1).order_by('id')
    serializer_class = WineSerializer
    pagination_class = PageNumberPagination

class AllWineList(generics.ListCreateAPIView):
    queryset =  Wine.objects.filter(visibility=1)
    serializer_class = WineSerializer
    pagination_class = None


class TransactionList(generics.ListCreateAPIView):
    queryset = Transaction.objects.filter(visibility=1).order_by('id')
    serializer_class = TransactionSerializer
    pagination_class = PageNumberPagination

class WineApiView(APIView):
    #authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        wine = Wine.objects.filter(id=pk).first()
        wine_serializer = WineSerializer(wine)
        return Response(wine_serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        wine_serializer = WineSerializer(data=request.data)
        if wine_serializer.is_valid():
            wine_serializer.save()
            return Response(wine_serializer.data, status=status.HTTP_201_CREATED)
        return Response(wine_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        wine = Wine.objects.filter(id=pk).first()
        if wine:
            wine_serializer = WineSerializer(wine, data=request.data)
            if wine_serializer.is_valid():
                wine_serializer.save()
                return Response(wine_serializer.data, status=status.HTTP_200_OK)
            return Response(wine_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': "Wine not found"}, status=status.HTTP_404_NOT_FOUND)

class TransactionApiView(APIView):
    #authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        transaction = Transaction.objects.filter(id=pk).first()
        if transaction:
            transaction_serializer = TransactionSerializer(transaction)
            return Response(transaction_serializer.data, status=status.HTTP_200_OK)
        return Response({'message': "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        transaction_serializer = TransactionSerializer(data=request.data)
        if transaction_serializer.is_valid():
            transaction_serializer.save()
            return Response(transaction_serializer.data, status=status.HTTP_201_CREATED)
        return Response(transaction_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        transaction = Transaction.objects.filter(id=pk).first()
        if transaction:
            transaction_serializer = TransactionSerializer(transaction, data=request.data)
            if transaction_serializer.is_valid():
                transaction_serializer.save()
                return Response(transaction_serializer.data, status=status.HTTP_201_CREATED)
            return Response(transaction_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
