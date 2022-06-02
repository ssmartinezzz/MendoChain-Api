from rest_framework import serializers
from .models import *
from .blockchain import *
import os
import json



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
        wine_name = getattr( validated_data['wine'], "variety_name")
        alcohol = getattr(validated_data['wine'], "alcohol")
        year =  getattr(validated_data['wine'], "year")
        content = getattr(validated_data['wine'], "content")
        lote = getattr(validated_data['wine'], "lote")
        brand = getattr(validated_data['wine'], "brand_name")
        message = f"Quantity: {validated_data['quantity']} \n " \
                  f"Wine: {wine_name}  \n " \
                  f"Alcohol: {alcohol}  \n " \
                  f"Year: {year}  \n" \
                  f"Content: {content}  \n " \
                  f"LotN° {lote} \n " \
                  f"Brand: {brand}"
        data = first_transaction_example(private_key=os.getenv("PRIVATE_KEY"), my_address=os.getenv("WALLET_ADD"), message=message)
        if data != "Error":
            return Transaction.objects.create(
                quantity=validated_data['quantity'],
                transaction_id=data,
                wine=validated_data['wine'],
                visibility=1,

            )
        
        raise serializers.ValidationError("Error while transaction")


    def update(self, instance, validated_data):
        instance.visibility = 0
        instance.wine = validated_data.get("wine")
        instance.quantity = validated_data.get("quantity")
        instance.transaction_id = validated_data.get("transaction_id")
        instance.save()
        return instance








