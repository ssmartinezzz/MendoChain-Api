from django.db import models
from django.contrib.auth.models import User

class Wine(models.Model):
    variety_name = models.CharField(max_length=100, null=False)

    content = models.CharField(max_length=5, null=False)

    alcohol = models.CharField(max_length=5, null=False)

    brand_name = models.CharField(max_length=100, null=False)

    lote = models.CharField(max_length=50, null=False)

    year = models.CharField(max_length=50, null=False)

    visibility = models.BooleanField(default=1)


class Transaction(models.Model):
    quantity = models.IntegerField(null=False)

    transaction_id = models.CharField(max_length=200, null=True)

    wine = models.ForeignKey(Wine, on_delete=models.CASCADE, related_name='transactions')

    visibility = models.BooleanField(default=1)




class Actor(models.Model):
    """Supply-chain participant with a custodial Algorand account."""

    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='actor')
    role = models.PositiveSmallIntegerField(choices=[(1, 'Winery'), (2, 'Distributor'), (3, 'Retailer')])
    address = models.CharField(max_length=58, unique=True)
    encrypted_private_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
