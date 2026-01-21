from django.contrib import admin
from .models import Post, Comentario


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "publicado",
        "destacado",
        "creado",
    )

    list_filter = (
        "publicado",
        "destacado",
        "creado",
    )

    search_fields = (
        "titulo",
        "resumen",
        "contenido",
    )

    prepopulated_fields = {
        "slug": ("titulo",)
    }

    list_editable = (
        "publicado",
        "destacado",
    )

    ordering = ("-creado",)

    fieldsets = (
        ("Contenido", {
            "fields": ("titulo", "slug", "resumen", "contenido", "imagen")
        }),
        ("Publicación", {
            "fields": ("publicado", "destacado")
        }),
    )


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "post",
        "aprobado",
        "creado",
    )

    list_filter = (
        "aprobado",
        "creado",
    )

    search_fields = (
        "usuario__username",
        "texto",
    )

    list_editable = (
        "aprobado",
    )

    ordering = ("-creado",)