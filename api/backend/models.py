from django.db import models
from django.contrib.auth.models import User

class Wine(models.Model):
    variety_name = models.CharField(max_length=100, null=False)

    content = models.CharField(max_length=5, null=False)

    alcohol = models.CharField(max_length=5, null=False)

    brand_name = models.CharField(max_length=100, null=False)

    lote = models.CharField(max_length=50, null=False)

    year = models.CharField(max_length=50, null=False)


class Transaction(models.Model):
    quantity = models.IntegerField(null=False)

    transaction_id = models.CharField(max_length=200, null=False)

    wine = models.ForeignKey(Wine, on_delete=models.CASCADE, related_name='transactions')


