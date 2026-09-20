from django.db import models

#CLASE PRODUCTO

from django.db import models


class Set(models.Model):
    tcgdex_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    logo = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Card(models.Model):
    tcgdex_id = models.CharField(max_length=100, unique=True)
    local_id = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    image = models.URLField(blank=True)
    category = models.CharField(max_length=50, blank=True)
    rarity = models.CharField(max_length=100, blank=True)
    illustrator = models.CharField(max_length=200, blank=True)

    set = models.ForeignKey(
        Set,
        on_delete=models.CASCADE,
        related_name="cards"
    )

    def __str__(self):
        return self.name


class Product(models.Model):
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.card.name if self.card else "Producto sin carta"