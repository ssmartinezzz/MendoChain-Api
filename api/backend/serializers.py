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

        )






