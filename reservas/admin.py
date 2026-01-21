from django.contrib import admin
from .models import Turno, ConfiguracionAgenda, DiaBloqueado


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    # 📋 Lo que ve Ludmila en la lista
    list_display = (
        "nombre_completo",
        "telefono",
        "fecha",
        "hora",
        "aceptado",
        "creado",
    )

    # 🔎 Filtros útiles
    list_filter = (
        "fecha",
        "aceptado",
    )

    # ✏️ Campos editables directamente desde la lista
    list_editable = (
        "aceptado",
    )

    # 🔍 Búsqueda rápida
    search_fields = (
        "nombre_completo",
        "telefono",
    )

    # 📐 Orden
    ordering = (
        "-fecha",
        "-hora",
    )

    # 🧾 Orden y permisos dentro del formulario
    fields = (
        "nombre_completo",
        "telefono",
        "fecha",
        "hora",
        "comentario",
        "aceptado",
        "comentario_ludmila",
        "creado",
    )

    readonly_fields = (
        "creado",
    )


@admin.register(ConfiguracionAgenda)
class ConfiguracionAgendaAdmin(admin.ModelAdmin):
    pass


@admin.register(DiaBloqueado)
class DiaBloqueadoAdmin(admin.ModelAdmin):
    pass