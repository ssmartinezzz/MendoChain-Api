import os

from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from .blockchain import BlockchainError, first_transaction_example
from .models import Transaction, Wine


class BlockchainUnavailable(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'The transaction could not be submitted to the blockchain.'
    default_code = 'blockchain_unavailable'


class WineSerializer(serializers.ModelSerializer):

    class Meta:
        model = Wine
        fields = '__all__'
        read_only_fields = ('visibility',)


class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('transaction_id', 'visibility')

    def create(self, validated_data):
        wine = validated_data['wine']
        message = f"Quantity: {validated_data['quantity']} \n " \
                  f"Wine: {wine.variety_name}  \n " \
                  f"Alcohol: {wine.alcohol}  \n " \
                  f"Year: {wine.year}  \n" \
                  f"Content: {wine.content}  \n " \
                  f"LotN° {wine.lote} \n " \
                  f"Brand: {wine.brand_name}"
        try:
            transaction_id = first_transaction_example(
                private_key=os.getenv("PRIVATE_KEY"), my_address=os.getenv("WALLET_ADD"), message=message,
            )
        except BlockchainError as err:
            raise BlockchainUnavailable() from err

        return Transaction.objects.create(
            quantity=validated_data['quantity'],
            transaction_id=transaction_id,
            wine=wine,
            visibility=True,
        )
