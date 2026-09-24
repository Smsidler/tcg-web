from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import CART_KEY, cart_items, read_cart, save_cart
from .forms import CartQuantityForm, CheckoutForm
from .models import Card, Order, OrderItem, Product, Set


SORT_OPTIONS = {
    "newest": ("-created_at", "-pk"),
    "price_asc": ("price", "pk"),
    "price_desc": ("-price", "pk"),
    "name": ("card__name", "pk"),
}


# Clave utilizada para guardar en la sesión los pedidos
# que fueron creados desde este navegador.
ORDER_SESSION_KEY = "accessible_orders"


def home(request):
    query = request.GET.get("q", "").strip()
    set_id = request.GET.get("set", "").strip()
    in_stock = request.GET.get("in_stock") == "1"
    sort = request.GET.get("sort", "newest")

    if sort not in SORT_OPTIONS:
        sort = "newest"

    products = (
        Product.objects
        .select_related("card", "card__set")
        .filter(card__isnull=False)
    )

    if query:
        products = products.filter(
            Q(card__name__icontains=query)
            | Q(card__set__name__icontains=query)
            | Q(card__rarity__icontains=query)
            | Q(card__local_id__icontains=query)
            | Q(sku__icontains=query)
        )

    if set_id:
        products = products.filter(
            card__set__tcgdex_id=set_id
        )

    if in_stock:
        products = products.filter(stock__gt=0)

    page = Paginator(
        products.order_by(*SORT_OPTIONS[sort]),
        12,
    ).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "products": page,
        "page_obj": page,
        "query": query,
        "selected_set": set_id,
        "in_stock": in_stock,
        "sort": sort,
        "sets": (
            Set.objects
            .filter(cards__products__isnull=False)
            .distinct()
            .order_by("name")
        ),
        "pagination_query": params.urlencode(),
    }

    return render(
        request,
        "products/home.html",
        context,
    )


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related(
            "card",
            "card__set",
        ),
        pk=pk,
        card__isnull=False,
    )

    variants = (
        Product.objects
        .filter(card=product.card)
        .exclude(pk=pk)
        .order_by("price", "pk")
    )

    return render(
        request,
        "products/product_detail.html",
        {
            "product": product,
            "variants": variants,
        },
    )


def legacy_card_detail(request, tcgdex_id):
    """Mantiene funcionando los enlaces antiguos de cartas."""

    card = get_object_or_404(
        Card,
        tcgdex_id=tcgdex_id,
    )

    products = (
        Product.objects
        .select_related("card", "card__set")
        .filter(card=card)
        .order_by("price", "pk")
    )

    if products.count() == 1:
        return redirect(
            "product_detail",
            pk=products.first().pk,
        )

    return render(
        request,
        "products/card_products.html",
        {
            "card": card,
            "products": products,
        },
    )


def cart_detail(request):
    items, total = cart_items(request.session)

    return render(
        request,
        "products/cart.html",
        {
            "items": items,
            "total": total,
        },
    )


def change_cart(request, pk, *, add):
    product = get_object_or_404(
        Product,
        pk=pk,
        card__isnull=False,
    )

    form = CartQuantityForm(request.POST)

    if not form.is_valid():
        messages.error(
            request,
            "Ingresa una cantidad entera entre 1 y 9999.",
        )
        return redirect("cart_detail")

    cart = read_cart(request.session)

    quantity = form.cleaned_data["quantity"]

    if add:
        quantity += cart.get(str(pk), 0)

    if quantity > product.stock or quantity > 9999:
        messages.error(
            request,
            (
                f"Stock insuficiente: quedan "
                f"{product.stock} unidades de "
                f"{product.card.name}."
            ),
        )
        return redirect("cart_detail")

    cart[str(pk)] = quantity
    save_cart(request.session, cart)

    messages.success(
        request,
        "Carrito actualizado.",
    )

    return redirect("cart_detail")


@require_POST
def cart_add(request, pk):
    return change_cart(
        request,
        pk,
        add=True,
    )


@require_POST
def cart_update(request, pk):
    return change_cart(
        request,
        pk,
        add=False,
    )


@require_POST
def cart_remove(request, pk):
    cart = read_cart(request.session)

    cart.pop(str(pk), None)

    save_cart(request.session, cart)

    messages.success(
        request,
        "Producto eliminado del carrito.",
    )

    return redirect("cart_detail")


def checkout(request):
    items, total = cart_items(request.session)

    if not items:
        messages.error(
            request,
            "Tu carrito está vacío.",
        )
        return redirect("cart_detail")

    if request.method == "POST":
        form = CheckoutForm(request.POST)

        if form.is_valid():
            cart = read_cart(request.session)

            try:
                with transaction.atomic():
                    product_ids = [
                        int(pk)
                        for pk in cart.keys()
                    ]

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
                        raise ValueError(
                            "Uno de los productos ya no está disponible."
                        )

                    order_total = 0

                    # Revalidamos el stock y calculamos
                    # nuevamente el total desde PostgreSQL.
                    for product_id in product_ids:
                        product = products[product_id]
                        quantity = cart[str(product_id)]

                        if quantity > product.stock:
                            raise ValueError(
                                (
                                    f"Stock insuficiente para "
                                    f"{product.card.name}. "
                                    f"Quedan {product.stock} unidades."
                                )
                            )

                        order_total += (
                            product.price * quantity
                        )

                    # Creamos el pedido.
                    order = form.save(commit=False)
                    order.total = order_total
                    order.save()

                    # Creamos los OrderItem y descontamos
                    # el inventario.
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

                        product.save(
                            update_fields=["stock"]
                        )

            except ValueError as exc:
                messages.error(
                    request,
                    str(exc),
                )
                return redirect("cart_detail")

            # La transacción terminó correctamente.
            # Ahora podemos vaciar el carrito.
            request.session[CART_KEY] = {}

            # Guardamos el UUID del pedido en la sesión.
            # Esto permite que únicamente el navegador
            # que creó el pedido pueda acceder a él.
            accessible_orders = request.session.get(
                ORDER_SESSION_KEY,
                [],
            )

            order_public_id = str(order.public_id)

            if order_public_id not in accessible_orders:
                accessible_orders.append(order_public_id)

            request.session[ORDER_SESSION_KEY] = accessible_orders
            request.session.modified = True

            return redirect(
                "order_success",
                public_id=order.public_id,
            )

    else:
        form = CheckoutForm()

    return render(
        request,
        "products/checkout.html",
        {
            "form": form,
            "items": items,
            "total": total,
        },
    )


def order_success(request, public_id):
    # Primero verificamos que este navegador haya creado
    # el pedido que está intentando consultar.
    accessible_orders = request.session.get(
        ORDER_SESSION_KEY,
        [],
    )

    if str(public_id) not in accessible_orders:
        # Respondemos como si el pedido no existiera.
        # De esta forma tampoco revelamos información
        # sobre la existencia de otros pedidos.
        get_object_or_404(
            Order,
            public_id=public_id,
            pk__in=[],
        )

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__product__card"
        ),
        public_id=public_id,
    )

    return render(
        request,
        "products/order_success.html",
        {
            "order": order,
        },
    )