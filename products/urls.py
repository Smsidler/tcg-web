from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),

    # Productos
    path(
        "products/<int:pk>/",
        views.product_detail,
        name="product_detail",
    ),
    path(
        "cards/<str:tcgdex_id>/",
        views.legacy_card_detail,
        name="legacy_card_detail",
    ),

    # Carrito
    path(
        "cart/",
        views.cart_detail,
        name="cart_detail",
    ),
    path(
        "cart/add/<int:pk>/",
        views.cart_add,
        name="cart_add",
    ),
    path(
        "cart/update/<int:pk>/",
        views.cart_update,
        name="cart_update",
    ),
    path(
        "cart/remove/<int:pk>/",
        views.cart_remove,
        name="cart_remove",
    ),

    # Checkout
    path(
        "checkout/",
        views.checkout,
        name="checkout",
    ),

    
    # Confirmación segura del pedido
    path(
        "orders/<uuid:public_id>/success/",
        views.order_success,
        name="order_success",
    ),
]
