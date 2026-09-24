from django.shortcuts import get_object_or_404
from rest_framework import generics

from .models import Transaction, Wine
from .serializers import TransactionSerializer, WineSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
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
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        # Soft-deleted wines stay retrievable so transaction history keeps resolving them.
        wine = get_object_or_404(Wine, id=pk)
        return Response(WineSerializer(wine).data, status=status.HTTP_200_OK)

    def post(self, request):
        wine_serializer = WineSerializer(data=request.data)
        if wine_serializer.is_valid():
            wine_serializer.save()
            return Response(wine_serializer.data, status=status.HTTP_201_CREATED)
        return Response(wine_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        wine = get_object_or_404(Wine, id=pk, visibility=True)
        wine_serializer = WineSerializer(wine, data=request.data)
        if wine_serializer.is_valid():
            wine_serializer.save()
            return Response(wine_serializer.data, status=status.HTTP_200_OK)
        return Response(wine_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        wine = get_object_or_404(Wine, id=pk, visibility=True)
        wine.visibility = False
        wine.save(update_fields=['visibility'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionApiView(APIView):
    """Transactions mirror immutable on-chain records, so they can be soft-deleted but not edited."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        transaction = get_object_or_404(Transaction, id=pk)
        return Response(TransactionSerializer(transaction).data, status=status.HTTP_200_OK)

    def post(self, request):
        transaction_serializer = TransactionSerializer(data=request.data)
        if transaction_serializer.is_valid():
            transaction_serializer.save()
            return Response(transaction_serializer.data, status=status.HTTP_201_CREATED)
        return Response(transaction_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        transaction = get_object_or_404(Transaction, id=pk, visibility=True)
        transaction.visibility = False
        transaction.save(update_fields=['visibility'])
        return Response(status=status.HTTP_204_NO_CONTENT)
