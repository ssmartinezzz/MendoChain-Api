from rest_framework import serializers
from .models import *
from .blockchain import *
import os



class WineSerializer(serializers.ModelSerializer):

    class Meta:
        model = Wine
        fields = '__all__'

    def update(self, instance, validated_data):
        instance.visibility = 0
        instance.variety_name = validated_data.get("variety_name")
        instance.content = validated_data.get("content")
        instance.alcohol = validated_data.get("alcohol")
        instance.lote = validated_data.get("lote")
        instance.year = validated_data.get("year")
        instance.save()
        return instance


class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transaction
        fields = '__all__'

    def create(self, validated_data):
        return Transaction.objects.create(
            quantity=validated_data['quantity'],
            transaction_id=first_transaction_example(private_key=os.getenv("PRIVATE_KEY"), my_address=os.getenv("WALLET_ADD")),
            wine=validated_data['wine'],
            visibility=1,
        )

    def update(self, instance, validated_data):
        instance.visibility = 0
        instance.wine = validated_data.get("wine")
        instance.quantity = validated_data.get("quantity")
        instance.transaction_id = validated_data.get("transaction_id")
        instance.save()
        return instance








