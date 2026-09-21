from django.contrib import admin
from django.utils.html import format_html

from .models import Card, Product, Set


def card_preview(card):
    if not card or not card.thumbnail_url:
        return "Sin imagen"
    return format_html(
        '<img src="{}" alt="{}" width="60" style="height: auto;" />',
        card.thumbnail_url, card.name,
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "sku", "card", "language", "condition", "variant", "price", "stock_status")
    search_fields = ("sku", "card__name", "card__tcgdex_id", "category")
    list_filter = ("language", "condition", "variant", "category", "card__set")
    list_select_related = ("card", "card__set")
    ordering = ("card__name", "pk")
    autocomplete_fields = ("card",)
    fieldsets = (
        ("Carta y versión", {"fields": ("card", "sku", "language", "condition", "variant")}),
        ("Precio e inventario", {"fields": ("price", "stock")}),
        ("Información adicional", {"fields": ("category", "description")}),
    )

    @admin.display(description="Imagen")
    def image_preview(self, obj):
        return card_preview(obj.card)

    @admin.display(description="Stock", ordering="stock")
    def stock_status(self, obj):
        if obj.stock == 0:
            color, label = "#dc3545", "Sin stock"
        elif obj.stock <= 5:
            color, label = "#9a5b00", f"Stock bajo ({obj.stock})"
        else:
            color, label = "#198754", f"Disponible ({obj.stock})"
        return format_html('<span style="color: {}; font-weight: bold;">● {}</span>', color, label)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "name", "set", "rarity", "category", "local_id")
    search_fields = ("name", "tcgdex_id", "local_id")
    list_filter = ("set", "rarity", "category")
    list_select_related = ("set",)
    ordering = ("name",)

    @admin.display(description="Imagen")
    def image_preview(self, obj):
        return card_preview(obj)


@admin.register(Set)
class SetAdmin(admin.ModelAdmin):
    list_display = ("name", "tcgdex_id")
    search_fields = ("name", "tcgdex_id")
    ordering = ("name",)
