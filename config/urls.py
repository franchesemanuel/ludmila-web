from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("blog/", include("blog.urls")),
    path("reservar/", include("reservas.urls")),
    path("users/", include("users.urls")),
]

# 🔥 SERVIR IMÁGENES EN DESARROLLO
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)