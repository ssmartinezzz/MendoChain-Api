"""HTTP adapters: parse input, call a use case, render output. No business rules here."""
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.traceability.application import selectors, services
from api.traceability.infrastructure.ledger import get_ledger
from api.traceability.interfaces.serializers import (
    MovementInputSerializer,
    MovementOutputSerializer,
    WineInputSerializer,
    WineOutputSerializer,
)


@api_view(['GET'])
def hello_world(request):
    name = "Anonymous" if request.user.is_anonymous else request.user.first_name
    return Response({"hello": f"Welcome to DRF, {name}!"}, 200)


class WineCollection(generics.ListAPIView):
    serializer_class = WineOutputSerializer

    def get_queryset(self):
        return selectors.active_wines()

    def post(self, request):
        data = _validated(WineInputSerializer, request)
        wine = services.register_wine(data)
        return Response(WineOutputSerializer(wine).data, status=status.HTTP_201_CREATED)


class AllWines(generics.ListAPIView):
    serializer_class = WineOutputSerializer
    pagination_class = None

    def get_queryset(self):
        return selectors.active_wines()


class WineDetail(generics.GenericAPIView):

    def get(self, request, pk):
        return Response(WineOutputSerializer(selectors.wine_by_id(pk)).data)

    def put(self, request, pk):
        data = _validated(WineInputSerializer, request)
        wine = services.update_wine(pk, data)
        return Response(WineOutputSerializer(wine).data)

    def delete(self, request, pk):
        services.retire_wine(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MovementCollection(generics.ListAPIView):
    serializer_class = MovementOutputSerializer

    def get_queryset(self):
        return selectors.active_movements()

    def post(self, request):
        data = _validated(MovementInputSerializer, request)
        movement = services.record_movement(wine=data['wine'], quantity=data['quantity'], ledger=get_ledger())
        return Response(MovementOutputSerializer(movement).data, status=status.HTTP_201_CREATED)


class MovementDetail(generics.GenericAPIView):

    def get(self, request, pk):
        return Response(MovementOutputSerializer(selectors.movement_by_id(pk)).data)

    def delete(self, request, pk):
        services.retire_movement(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _validated(serializer_class, request):
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data
