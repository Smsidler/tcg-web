from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from .models import Product


def home(request):
    query = request.GET.get("q", "").strip()

    products = Product.objects.select_related(
        "card",
        "card__set"
    ).filter(card__isnull=False)

    if query:
        products = products.filter(
            Q(card__name__icontains=query) |
            Q(card__set__name__icontains=query) |
            Q(card__rarity__icontains=query) |
            Q(card__local_id__icontains=query)
        )

    context = {
        "products": products,
        "query": query,
    }

    return render(request, "products/home.html", context)


def product_detail(request, tcgdex_id):
    product = get_object_or_404(
        Product.objects.select_related("card", "card__set"),
        card__tcgdex_id=tcgdex_id
    )

    context = {
        "product": product,
    }

    return render(request, "products/product_detail.html", context)