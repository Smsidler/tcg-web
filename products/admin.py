from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.html import format_html

from .models import Card, Order, OrderItem, Product, Set


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def card_preview(card):
    if not card or not card.thumbnail_url:
        return "Sin imagen"

    return format_html(
        '<img src="{}" alt="{}" width="60" '
        'style="height: auto; border-radius: 6px;" />',
        card.thumbnail_url,
        card.name,
    )


# =========================================================
# PRODUCTOS
# =========================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview",
        "sku",
        "card",
        "language",
        "condition",
        "variant",
        "price",
        "stock_status",
    )

    search_fields = (
        "sku",
        "card__name",
        "card__tcgdex_id",
        "category",
    )

    list_filter = (
        "language",
        "condition",
        "variant",
        "category",
        "card__set",
    )

    list_select_related = (
        "card",
        "card__set",
    )

    ordering = (
        "card__name",
        "pk",
    )

    autocomplete_fields = (
        "card",
    )

    fieldsets = (
        (
            "Carta y versión",
            {
                "fields": (
                    "card",
                    "sku",
                    "language",
                    "condition",
                    "variant",
                )
            },
        ),
        (
            "Precio e inventario",
            {
                "fields": (
                    "price",
                    "stock",
                )
            },
        ),
        (
            "Información adicional",
            {
                "fields": (
                    "category",
                    "description",
                )
            },
        ),
    )

    @admin.display(description="Imagen")
    def image_preview(self, obj):
        return card_preview(obj.card)

    @admin.display(description="Stock", ordering="stock")
    def stock_status(self, obj):
        if obj.stock == 0:
            color = "#dc3545"
            label = "Sin stock"

        elif obj.stock <= 5:
            color = "#9a5b00"
            label = f"Stock bajo ({obj.stock})"

        else:
            color = "#198754"
            label = f"Disponible ({obj.stock})"

        return format_html(
            '<span style="color: {}; font-weight: bold;">'
            "● {}"
            "</span>",
            color,
            label,
        )


# =========================================================
# CARTAS
# =========================================================

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview",
        "name",
        "set",
        "rarity",
        "category",
        "local_id",
    )

    search_fields = (
        "name",
        "tcgdex_id",
        "local_id",
    )

    list_filter = (
        "set",
        "rarity",
        "category",
    )

    list_select_related = (
        "set",
    )

    ordering = (
        "name",
    )

    @admin.display(description="Imagen")
    def image_preview(self, obj):
        return card_preview(obj)


# =========================================================
# SETS
# =========================================================

@admin.register(Set)
class SetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tcgdex_id",
    )

    search_fields = (
        "name",
        "tcgdex_id",
    )

    ordering = (
        "name",
    )


# =========================================================
# ITEMS DEL PEDIDO
# =========================================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem

    extra = 0

    fields = (
        "product",
        "quantity",
        "unit_price",
        "item_subtotal",
    )

    readonly_fields = (
        "product",
        "quantity",
        "unit_price",
        "item_subtotal",
    )

    can_delete = False

    @admin.display(description="Subtotal")
    def item_subtotal(self, obj):
        if not obj.pk:
            return "-"

        return f"${obj.subtotal:,.0f}".replace(",", ".")


# =========================================================
# PEDIDOS
# =========================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "name",
        "email",
        "formatted_total",
        "status_badge",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "=id",
        "name",
        "email",
        "phone",
        "address",
        "commune",
        "items__product__sku",
        "items__product__card__name",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "created_at"

    readonly_fields = (
        "created_at",
        "formatted_total_detail",
    )

    fieldsets = (
        (
            "Pedido",
            {
                "fields": (
                    "status",
                    "created_at",
                    "formatted_total_detail",
                )
            },
        ),
        (
            "Cliente",
            {
                "fields": (
                    "name",
                    "email",
                    "phone",
                )
            },
        ),
        (
            "Entrega",
            {
                "fields": (
                    "address",
                    "commune",
                    "notes",
                )
            },
        ),
    )

    inlines = (
        OrderItemInline,
    )

    # =====================================================
    # INFORMACIÓN DEL PEDIDO
    # =====================================================

    @admin.display(description="Pedido", ordering="id")
    def order_number(self, obj):
        return f"#{obj.pk}"

    @admin.display(description="Total", ordering="total")
    def formatted_total(self, obj):
        return f"${obj.total:,.0f}".replace(",", ".")

    @admin.display(description="Total")
    def formatted_total_detail(self, obj):
        if not obj.pk:
            return "-"

        return f"${obj.total:,.0f}".replace(",", ".")

    # =====================================================
    # ESTADO VISUAL
    # =====================================================

    @admin.display(description="Estado", ordering="status")
    def status_badge(self, obj):
        colors = {
            Order.Status.PENDING: (
                "#9a5b00",
                "#fff7d6",
            ),
            Order.Status.PAID: (
                "#166534",
                "#dcfce7",
            ),
            Order.Status.PREPARING: (
                "#1d4ed8",
                "#dbeafe",
            ),
            Order.Status.SHIPPED: (
                "#6d28d9",
                "#ede9fe",
            ),
            Order.Status.COMPLETED: (
                "#166534",
                "#dcfce7",
            ),
            Order.Status.CANCELLED: (
                "#b91c1c",
                "#fee2e2",
            ),
        }

        color, background = colors.get(
            obj.status,
            (
                "#334155",
                "#f1f5f9",
            ),
        )

        return format_html(
            '<span style="'
            "display: inline-block;"
            "padding: 4px 9px;"
            "border-radius: 999px;"
            "font-weight: 700;"
            "color: {};"
            "background: {};"
            '">{}</span>',
            color,
            background,
            obj.get_status_display(),
        )

    # =====================================================
    # CONTROL AUTOMÁTICO DEL INVENTARIO
    # =====================================================

    def save_model(self, request, obj, form, change):

        # Si se está creando un pedido nuevo desde el admin,
        # dejamos que Django lo guarde normalmente.
        if not change:
            super().save_model(
                request,
                obj,
                form,
                change,
            )
            return

        with transaction.atomic():

            # Bloqueamos el pedido mientras procesamos
            # el cambio de estado.
            current_order = (
                Order.objects
                .select_for_update()
                .get(pk=obj.pk)
            )

            old_status = current_order.status
            new_status = obj.status

            # =================================================
            # CASO 1:
            # CANCELAR UN PEDIDO
            # =================================================

            if (
                new_status == Order.Status.CANCELLED
                and not current_order.stock_restored
            ):

                # Obtenemos los productos y cantidades
                # que pertenecen al pedido.
                items = list(
                    current_order.items.all()
                )

                product_ids = [
                    item.product_id
                    for item in items
                ]

                # IMPORTANTE:
                # Bloqueamos directamente Product.
                #
                # No usamos select_related("card") aquí
                # porque Product.card puede ser NULL y
                # PostgreSQL no permite FOR UPDATE sobre
                # el lado nullable de ese OUTER JOIN.
                products = {
                    product.pk: product
                    for product in (
                        Product.objects
                        .select_for_update()
                        .filter(pk__in=product_ids)
                    )
                }

                # Restauramos las unidades del pedido.
                for item in items:

                    product = products.get(
                        item.product_id
                    )

                    if product is None:
                        raise ValidationError(
                            (
                                "No se pudo restaurar el stock "
                                "porque uno de los productos "
                                "del pedido ya no existe."
                            )
                        )

                    product.stock += item.quantity

                    product.save(
                        update_fields=["stock"]
                    )

                # Marcamos que este pedido YA devolvió
                # sus unidades.
                #
                # Esto evita que guardar nuevamente el
                # pedido como Cancelado vuelva a sumar stock.
                obj.stock_restored = True

                messages.success(
                    request,
                    (
                        "Pedido cancelado. "
                        "El stock fue restaurado automáticamente."
                    ),
                )

            # =================================================
            # CASO 2:
            # REACTIVAR UN PEDIDO CANCELADO
            # =================================================

            elif (
                old_status == Order.Status.CANCELLED
                and new_status != Order.Status.CANCELLED
                and current_order.stock_restored
            ):

                items = list(
                    current_order.items.all()
                )

                product_ids = [
                    item.product_id
                    for item in items
                ]

                # Bloqueamos los productos involucrados.
                #
                # Aquí tampoco usamos select_related("card")
                # junto con select_for_update.
                products = {
                    product.pk: product
                    for product in (
                        Product.objects
                        .select_for_update()
                        .filter(pk__in=product_ids)
                    )
                }

                # ---------------------------------------------
                # PRIMERO:
                # comprobamos que TODOS tengan stock.
                # ---------------------------------------------

                for item in items:

                    product = products.get(
                        item.product_id
                    )

                    if product is None:
                        raise ValidationError(
                            (
                                "No se puede reactivar el pedido "
                                "porque uno de sus productos "
                                "ya no está disponible."
                            )
                        )

                    if product.stock < item.quantity:

                        # Consultamos el nombre de la carta
                        # solamente si necesitamos mostrar
                        # el error.
                        card_name = (
                            product.card.name
                            if product.card
                            else product.sku
                        )

                        raise ValidationError(
                            (
                                "No se puede reactivar el pedido. "
                                f"{card_name} tiene "
                                f"{product.stock} unidades disponibles "
                                "y el pedido necesita "
                                f"{item.quantity}."
                            )
                        )

                # ---------------------------------------------
                # SEGUNDO:
                # descontamos las unidades.
                #
                # Solo llegamos aquí si TODO el pedido
                # tiene inventario suficiente.
                # ---------------------------------------------

                for item in items:

                    product = products[
                        item.product_id
                    ]

                    product.stock -= item.quantity

                    product.save(
                        update_fields=["stock"]
                    )

                # El inventario vuelve a estar comprometido
                # por este pedido.
                obj.stock_restored = False

                messages.success(
                    request,
                    (
                        "Pedido reactivado. "
                        "El stock fue descontado nuevamente."
                    ),
                )

            # =================================================
            # GUARDAR PEDIDO
            # =================================================

            super().save_model(
                request,
                obj,
                form,
                change,
            )