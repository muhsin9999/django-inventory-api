from django.db import models


class Product(models.Model):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=0)


class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    kind = models.CharField(max_length=3, choices=[('in', 'In'), ('out', 'Out')])
    amount = models.PositiveIntegerField()
    reference = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
