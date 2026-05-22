from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from reservas.models import Turno


# ─── Inline: citas de cada usuario ───────────────────────────────────────────
class TurnoInline(admin.TabularInline):
    model          = Turno
    extra          = 0
    can_delete     = False
    show_change_link = True
    verbose_name   = "Cita"
    verbose_name_plural = "Historial de citas"

    fields         = ("fecha", "hora", "servicio", "estado_inline", "comentario_ludmila")
    readonly_fields = ("fecha", "hora", "servicio", "estado_inline", "comentario_ludmila")
    ordering       = ("-fecha", "-hora")

    def estado_inline(self, obj):
        if obj.cancelado:
            return format_html('<span style="color:#dc3545;font-weight:600;">Cancelada</span>')
        if obj.aceptado:
            return format_html('<span style="color:#198754;font-weight:600;">✓ Confirmada</span>')
        return format_html('<span style="color:#fd7e14;font-weight:600;">Pendiente</span>')
    estado_inline.short_description = "Estado"


# ─── UserAdmin extendido ──────────────────────────────────────────────────────
class ClienteAdmin(UserAdmin):
    inlines = [TurnoInline]

    list_display = (
        "username", "first_name", "last_name",
        "total_citas", "citas_completadas", "is_active", "date_joined",
    )
    list_filter = ("is_active", "is_staff", "date_joined")

    def total_citas(self, obj):
        n = obj.turnos.filter(cancelado=False).count()
        return format_html('<strong>{}</strong>', n)
    total_citas.short_description = "Citas activas"

    def citas_completadas(self, obj):
        from django.utils import timezone
        n = obj.turnos.filter(cancelado=False, fecha__lt=timezone.localdate()).count()
        return n
    citas_completadas.short_description = "Realizadas"


admin.site.unregister(User)
admin.site.register(User, ClienteAdmin)
