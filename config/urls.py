from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Administración TCG Web"
admin.site.site_title = "TCG Web Admin"
admin.site.index_title = "Gestión de la tienda"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
]
