from django.contrib import admin
from django.utils.html import mark_safe

from .models import Set, Card, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview",
        "card",
        "price",
        "stock_status",
        "category",
        "created_at",
    )

    search_fields = ("card__name", "category")
    list_filter = ("category", "stock")
    ordering = ("card__name",)
    autocomplete_fields = ("card",)
    
    fieldsets = (
    ("Carta", {
        "fields": ("card",)
    }),
    ("Precio e inventario", {
        "fields": ("price", "stock")
    }),
    ("Información adicional", {
        "fields": ("category", "description")
    }),
)
    
    @admin.display(description="Imagen")
    def image_preview(self, obj):
        if obj.card and obj.card.image:
            image_url = f"{obj.card.image}/low.webp"

            return mark_safe(
                f'<img src="{image_url}" width="60" style="height: auto;" />'
            )

        return "Sin imagen"

    @admin.display(description="Stock", ordering="stock")
    def stock_status(self, obj):
        if obj.stock == 0:
            return mark_safe(
                '<span style="color: #dc3545; font-weight: bold;">● Sin stock</span>'
            )

        elif obj.stock <= 5:
            return mark_safe(
                f'<span style="color: #fd7e14; font-weight: bold;">● Stock bajo ({obj.stock})</span>'
            )

        return mark_safe(
            f'<span style="color: #198754; font-weight: bold;">● Disponible ({obj.stock})</span>'
        )

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "name", "set", "rarity", "category", "local_id")
    search_fields = ("name", "tcgdex_id", "local_id")
    list_filter = ("set", "rarity", "category")
    ordering = ("name",)

    @admin.display(description="Imagen")
    def image_preview(self, obj):
        if obj.image:
            image_url = f"{obj.image}/low.webp"

        return mark_safe(
            f'<img src="{image_url}" width="60" style="height: auto;" />'
        )

        return "Sin imagen"

@admin.register(Set)
class SetAdmin(admin.ModelAdmin):
    list_display = ("name", "tcgdex_id")
    search_fields = ("name", "tcgdex_id")
    ordering = ("name",)