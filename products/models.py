from decimal import Decimal
from uuid import uuid4

from django.core.validators import MinValueValidator
from django.db import models


def generate_sku():
    return f"TCG-{uuid4().hex.upper()}"


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
    set = models.ForeignKey(Set, on_delete=models.PROTECT, related_name="cards")

    @property
    def image_url(self):
        return f"{self.image.rstrip('/')}/high.webp" if self.image else ""

    @property
    def thumbnail_url(self):
        return f"{self.image.rstrip('/')}/low.webp" if self.image else ""

    def __str__(self):
        return f"{self.name} ({self.tcgdex_id})"


class Product(models.Model):
    class Language(models.TextChoices):
        UNKNOWN = "unknown", "Por definir"
        ENGLISH = "en", "Inglés"
        SPANISH = "es", "Español"
        JAPANESE = "ja", "Japonés"
        OTHER = "other", "Otro"

    class Condition(models.TextChoices):
        UNKNOWN = "unknown", "Por definir"
        NEAR_MINT = "NM", "Near Mint"
        LIGHTLY_PLAYED = "LP", "Lightly Played"
        MODERATELY_PLAYED = "MP", "Moderately Played"
        HEAVILY_PLAYED = "HP", "Heavily Played"
        DAMAGED = "DMG", "Dañada"

    class Variant(models.TextChoices):
        UNKNOWN = "unknown", "Por definir"
        NORMAL = "normal", "Normal"
        HOLO = "holo", "Holo"
        REVERSE = "reverse", "Reverse Holo"
        OTHER = "other", "Otra"

    card = models.ForeignKey(
        Card, on_delete=models.PROTECT, related_name="products", null=True, blank=True
    )
    sku = models.CharField(max_length=40, unique=True, default=generate_sku)
    language = models.CharField(max_length=10, choices=Language.choices, default=Language.UNKNOWN)
    condition = models.CharField(max_length=10, choices=Condition.choices, default=Condition.UNKNOWN)
    variant = models.CharField(max_length=10, choices=Variant.choices, default=Variant.UNKNOWN)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    stock = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="product_price_nonnegative")
        ]

    def __str__(self):
        name = self.card.name if self.card else "Producto sin carta"
        return f"{name} · {self.sku}"
