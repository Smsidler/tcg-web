from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
]


# Servir archivos multimedia localmente solo cuando
# NO estamos utilizando Neon Object Storage / S3.
if settings.DEBUG and not settings.USE_S3_STORAGE:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )