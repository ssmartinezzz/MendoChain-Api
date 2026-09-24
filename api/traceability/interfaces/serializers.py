"""Input and output DTOs. Input serializers only validate; output serializers only render."""
from rest_framework import serializers

from api.traceability.models import Transaction, Wine

WINE_FIELDS = ('variety_name', 'content', 'alcohol', 'brand_name', 'lote', 'year')


class WineInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wine
        fields = WINE_FIELDS


class WineOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wine
        fields = ('id', *WINE_FIELDS, 'visibility')
        read_only_fields = fields


class MovementInputSerializer(serializers.Serializer):
    wine = serializers.PrimaryKeyRelatedField(queryset=Wine.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class MovementOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'quantity', 'transaction_id', 'wine', 'visibility')
        read_only_fields = fields
