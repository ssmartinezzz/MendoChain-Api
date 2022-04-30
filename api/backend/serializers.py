from rest_framework import serializers
from .models import *


class WineSerializer(serializers.ModelSerializer):

    class Meta:
        model = Wine
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transaction
        fields = '__all__'

