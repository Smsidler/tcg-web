"""Session storage contains only product IDs and quantities, never prices."""
from decimal import Decimal

from .models import Product

CART_KEY = "cart"


def read_cart(session):
    raw = session.get(CART_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {
        key: quantity for key, quantity in raw.items()
        if isinstance(key, str) and key.isascii() and key.isdigit()
        and 0 < len(key) <= 18 and int(key) > 0
        and type(quantity) is int and 1 <= quantity <= 9999
    }


def save_cart(session, cart):
    session[CART_KEY] = cart


def cart_items(session):
    cart = read_cart(session)
    products = Product.objects.select_related("card", "card__set").filter(
        pk__in=cart, card__isnull=False
    ).order_by("pk")
    items = []
    total = Decimal("0")
    valid_cart = {}
    for product in products:
        quantity = cart[str(product.pk)]
        subtotal = product.price * quantity
        items.append({
            "product": product, "quantity": quantity, "subtotal": subtotal,
            "available": product.stock >= quantity,
        })
        valid_cart[str(product.pk)] = quantity
        total += subtotal
    if session.get(CART_KEY, {}) != valid_cart:
        save_cart(session, valid_cart)
    return items, total
