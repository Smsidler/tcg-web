from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import cart_items, read_cart, save_cart
from .forms import CartQuantityForm
from .models import Card, Product, Set

SORT_OPTIONS = {
    "newest": ("-created_at", "-pk"),
    "price_asc": ("price", "pk"),
    "price_desc": ("-price", "pk"),
    "name": ("card__name", "pk"),
}


def home(request):
    query = request.GET.get("q", "").strip()
    set_id = request.GET.get("set", "").strip()
    in_stock = request.GET.get("in_stock") == "1"
    sort = request.GET.get("sort", "newest")
    if sort not in SORT_OPTIONS:
        sort = "newest"
    products = Product.objects.select_related("card", "card__set").filter(card__isnull=False)
    if query:
        products = products.filter(
            Q(card__name__icontains=query) | Q(card__set__name__icontains=query)
            | Q(card__rarity__icontains=query) | Q(card__local_id__icontains=query)
            | Q(sku__icontains=query)
        )
    if set_id:
        products = products.filter(card__set__tcgdex_id=set_id)
    if in_stock:
        products = products.filter(stock__gt=0)
    page = Paginator(products.order_by(*SORT_OPTIONS[sort]), 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    context = {
        "products": page, "page_obj": page, "query": query,
        "selected_set": set_id, "in_stock": in_stock, "sort": sort,
        "sets": Set.objects.filter(cards__products__isnull=False).distinct().order_by("name"),
        "pagination_query": params.urlencode(),
    }
    return render(request, "products/home.html", context)


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("card", "card__set"), pk=pk, card__isnull=False
    )
    variants = Product.objects.filter(card=product.card).exclude(pk=pk).order_by("price", "pk")
    return render(request, "products/product_detail.html", {"product": product, "variants": variants})


def legacy_card_detail(request, tcgdex_id):
    """Keep existing card links usable without selecting an arbitrary variant."""
    card = get_object_or_404(Card, tcgdex_id=tcgdex_id)
    products = Product.objects.select_related("card", "card__set").filter(card=card).order_by("price", "pk")
    if products.count() == 1:
        return redirect("product_detail", pk=products.first().pk)
    return render(request, "products/card_products.html", {"card": card, "products": products})


def cart_detail(request):
    items, total = cart_items(request.session)
    return render(request, "products/cart.html", {"items": items, "total": total})


def change_cart(request, pk, *, add):
    product = get_object_or_404(Product, pk=pk, card__isnull=False)
    form = CartQuantityForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Ingresa una cantidad entera entre 1 y 9999.")
        return redirect("cart_detail")
    cart = read_cart(request.session)
    quantity = form.cleaned_data["quantity"] + (cart.get(str(pk), 0) if add else 0)
    if quantity > product.stock or quantity > 9999:
        messages.error(request, f"Stock insuficiente: quedan {product.stock} unidades de {product.card.name}.")
        return redirect("cart_detail")
    cart[str(pk)] = quantity
    save_cart(request.session, cart)
    messages.success(request, "Carrito actualizado.")
    return redirect("cart_detail")


@require_POST
def cart_add(request, pk):
    return change_cart(request, pk, add=True)


@require_POST
def cart_update(request, pk):
    return change_cart(request, pk, add=False)


@require_POST
def cart_remove(request, pk):
    cart = read_cart(request.session)
    cart.pop(str(pk), None)
    save_cart(request.session, cart)
    messages.success(request, "Producto eliminado del carrito.")
    return redirect("cart_detail")
