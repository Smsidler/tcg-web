from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Order, OrderItem, Product


class OrderError(ValueError):
    """Error esperado durante una operación de pedido."""


@transaction.atomic
def create_order(*, cleaned_data, cart):
    """
    Crea un pedido desde un carrito ya validado.

    - Bloquea los productos involucrados.
    - Vuelve a comprobar disponibilidad y stock.
    - Calcula el total usando precios de la base de datos.
    - Crea Order y OrderItem.
    - Descuenta el inventario.

    Devuelve el Order creado.
    """

    product_ids = [int(pk) for pk in cart.keys()]

    products = {
        product.pk: product
        for product in (
            Product.objects
            .select_for_update()
            .select_related("card")
            .filter(
                pk__in=product_ids,
                card__isnull=False,
            )
        )
    }

    if len(products) != len(product_ids):
        raise OrderError(
            "Uno de los productos ya no está disponible."
        )

    order_total = 0

    # Primero validamos TODO el pedido.
    # No modificamos inventario hasta comprobar que
    # todos los productos tienen stock suficiente.
    for product_id in product_ids:
        product = products[product_id]
        quantity = cart[str(product_id)]

        if quantity > product.stock:
            raise OrderError(
                f"Stock insuficiente para {product.card.name}. "
                f"Quedan {product.stock} unidades."
            )

        order_total += product.price * quantity

    order = Order.objects.create(
        **cleaned_data,
        total=order_total,
    )

    # Solo después de validar todo el pedido modificamos stock.
    for product_id in product_ids:
        product = products[product_id]
        quantity = cart[str(product_id)]

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.price,
        )

        product.stock -= quantity
        product.save(update_fields=["stock"])

    return order


@transaction.atomic
def cancel_order(order):
    """
    Cancela un pedido y restaura su inventario.

    Si el stock ya fue restaurado anteriormente,
    no vuelve a sumarlo.
    """

    current_order = (
        Order.objects
        .select_for_update()
        .get(pk=order.pk)
    )

    if current_order.stock_restored:
        current_order.status = Order.Status.CANCELLED
        current_order.save(update_fields=["status"])
        return current_order

    items = list(current_order.items.all())

    product_ids = [
        item.product_id
        for item in items
    ]

    products = {
        product.pk: product
        for product in (
            Product.objects
            .select_for_update()
            .filter(pk__in=product_ids)
        )
    }

    for item in items:
        product = products.get(item.product_id)

        if product is None:
            raise ValidationError(
                "No se pudo restaurar el stock porque uno "
                "de los productos del pedido ya no existe."
            )

        product.stock += item.quantity
        product.save(update_fields=["stock"])

    current_order.status = Order.Status.CANCELLED
    current_order.stock_restored = True

    current_order.save(
        update_fields=[
            "status",
            "stock_restored",
        ]
    )

    return current_order


@transaction.atomic
def reactivate_order(order, new_status):
    """
    Reactiva un pedido cancelado.

    Comprueba primero que todos los productos tengan
    stock suficiente y luego vuelve a descontarlo.
    """

    if new_status == Order.Status.CANCELLED:
        raise ValidationError(
            "El nuevo estado debe ser distinto de Cancelado."
        )

    current_order = (
        Order.objects
        .select_for_update()
        .get(pk=order.pk)
    )

    if not current_order.stock_restored:
        current_order.status = new_status
        current_order.save(update_fields=["status"])
        return current_order

    items = list(current_order.items.all())

    product_ids = [
        item.product_id
        for item in items
    ]

    products = {
        product.pk: product
        for product in (
            Product.objects
            .select_for_update()
            .filter(pk__in=product_ids)
        )
    }

    # Validamos todo antes de descontar una sola unidad.
    for item in items:
        product = products.get(item.product_id)

        if product is None:
            raise ValidationError(
                "No se puede reactivar el pedido porque "
                "uno de sus productos ya no está disponible."
            )

        if product.stock < item.quantity:
            card_name = (
                product.card.name
                if product.card
                else product.sku
            )

            raise ValidationError(
                "No se puede reactivar el pedido. "
                f"{card_name} tiene {product.stock} "
                "unidades disponibles y el pedido necesita "
                f"{item.quantity}."
            )

    # Solo después de validar todo descontamos inventario.
    for item in items:
        product = products[item.product_id]

        product.stock -= item.quantity
        product.save(update_fields=["stock"])

    current_order.status = new_status
    current_order.stock_restored = False

    current_order.save(
        update_fields=[
            "status",
            "stock_restored",
        ]
    )

    return current_order