import datetime
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils import timezone
from django.utils.html import format_html
from .models import Turno, ConfiguracionAgenda, DiaBloqueado, Servicio


# ─── Acciones en masa ─────────────────────────────────────────────────────────
@admin.action(description="✅ Confirmar citas seleccionadas")
def confirmar_turnos(modeladmin, request, queryset):
    queryset.filter(cancelado=False).update(aceptado=True)


@admin.action(description="❌ Cancelar citas seleccionadas")
def cancelar_turnos(modeladmin, request, queryset):
    queryset.update(cancelado=True, aceptado=False)


# ─── Servicios ────────────────────────────────────────────────────────────────
@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display  = ("nombre", "categoria", "duracion_minutos", "precio", "activo", "orden")
    list_editable = ("activo", "orden", "precio")
    list_filter   = ("activo", "categoria")
    ordering      = ("categoria", "orden")


# ─── Turnos ───────────────────────────────────────────────────────────────────
@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):

    list_display   = (
        "hora_chip", "nombre_completo", "telefono",
        "servicio_col", "fecha", "estado_badge", "aceptado",
    )
    list_editable  = ("aceptado",)
    list_filter    = ("fecha", "aceptado", "cancelado", "servicio")
    search_fields  = ("nombre_completo", "telefono", "usuario__username")
    ordering       = ("-fecha", "hora")
    date_hierarchy = "fecha"
    actions        = [confirmar_turnos, cancelar_turnos]

    fields = (
        "usuario", "nombre_completo", "telefono", "servicio",
        "fecha", "hora", "comentario",
        "aceptado", "cancelado", "comentario_ludmila",
        "creado",
    )
    readonly_fields = ("creado",)

    # ── Columnas personalizadas ──────────────────────────────────────────────

    def hora_chip(self, obj):
        return format_html(
            '<span style="background:#417690;color:#fff;padding:3px 10px;'
            'border-radius:20px;font-size:0.8rem;font-weight:600;">{}</span>',
            obj.hora.strftime("%H:%M"),
        )
    hora_chip.short_description = "Hora"
    hora_chip.admin_order_field = "hora"

    def servicio_col(self, obj):
        if obj.servicio:
            return format_html(
                "{}<br><small style='color:#aaa;'>{} min</small>",
                obj.servicio.nombre,
                obj.servicio.duracion_minutos,
            )
        return "—"
    servicio_col.short_description = "Servicio"
    servicio_col.admin_order_field = "servicio__nombre"

    def estado_badge(self, obj):
        if obj.cancelado:
            return format_html(
                '<span style="background:#f8d7da;color:#58151c;padding:3px 10px;'
                'border-radius:20px;font-size:0.75rem;font-weight:600;">Cancelada</span>'
            )
        if obj.aceptado:
            return format_html(
                '<span style="background:#d1e7dd;color:#0a3622;padding:3px 10px;'
                'border-radius:20px;font-size:0.75rem;font-weight:600;">✓ Confirmada</span>'
            )
        return format_html(
            '<span style="background:#fff3cd;color:#664d03;padding:3px 10px;'
            'border-radius:20px;font-size:0.75rem;font-weight:600;">Pendiente</span>'
        )
    estado_badge.short_description = "Estado"

    # ── Vista de agenda del día ──────────────────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "agenda/",
                self.admin_site.admin_view(self.agenda_view),
                name="reservas_agenda",
            ),
            path(
                "semana/",
                self.admin_site.admin_view(self.semana_view),
                name="reservas_semana",
            ),
        ]
        return extra + urls

    def agenda_view(self, request):
        fecha_str = request.GET.get("fecha")
        try:
            fecha = datetime.date.fromisoformat(fecha_str) if fecha_str else timezone.localdate()
        except ValueError:
            fecha = timezone.localdate()

        turnos = (
            Turno.objects
            .filter(fecha=fecha, cancelado=False)
            .select_related("servicio", "usuario")
            .order_by("hora")
        )

        total       = turnos.count()
        confirmadas = turnos.filter(aceptado=True).count()
        pendientes  = turnos.filter(aceptado=False).count()

        context = {
            **self.admin_site.each_context(request),
            "title":       f"Agenda — {fecha.strftime('%d/%m/%Y')}",
            "turnos":      turnos,
            "fecha":       fecha,
            "prev_fecha":  fecha - datetime.timedelta(days=1),
            "next_fecha":  fecha + datetime.timedelta(days=1),
            "hoy":         timezone.localdate(),
            "total":       total,
            "confirmadas": confirmadas,
            "pendientes":  pendientes,
        }
        return render(request, "admin/reservas/agenda.html", context)

    def semana_view(self, request):
        semana_str = request.GET.get("semana")
        try:
            lunes = datetime.date.fromisoformat(semana_str) if semana_str else None
        except ValueError:
            lunes = None

        if not lunes:
            hoy = timezone.localdate()
            lunes = hoy - datetime.timedelta(days=hoy.weekday())

        dias_semana = [lunes + datetime.timedelta(days=i) for i in range(7)]

        config = ConfiguracionAgenda.objects.first()
        if config:
            hora_inicio  = config.hora_inicio
            hora_fin     = config.hora_fin
            intervalo    = config.intervalo_minutos
            dias_trabaja = [
                config.trabaja_lunes, config.trabaja_martes, config.trabaja_miercoles,
                config.trabaja_jueves, config.trabaja_viernes,
                config.trabaja_sabado, config.trabaja_domingo,
            ]
        else:
            hora_inicio  = datetime.time(9, 0)
            hora_fin     = datetime.time(18, 0)
            intervalo    = 30
            dias_trabaja = [True, True, True, True, True, False, False]

        # Generar franjas horarias
        slots = []
        cur = datetime.datetime.combine(datetime.date.today(), hora_inicio)
        fin = datetime.datetime.combine(datetime.date.today(), hora_fin)
        while cur < fin:
            slots.append(cur.time())
            cur += datetime.timedelta(minutes=intervalo)

        domingo = lunes + datetime.timedelta(days=6)
        turnos_semana = (
            Turno.objects
            .filter(fecha__range=(lunes, domingo))
            .select_related("servicio", "usuario")
        )
        turno_map = {(t.fecha, t.hora): t for t in turnos_semana}

        dias_bloqueados = set(
            DiaBloqueado.objects
            .filter(fecha__range=(lunes, domingo))
            .values_list("fecha", flat=True)
        )

        # Armar grilla
        grid = []
        for slot in slots:
            row = {"hora": slot, "celdas": []}
            for i, dia in enumerate(dias_semana):
                if not dias_trabaja[i] or dia in dias_bloqueados:
                    row["celdas"].append({"tipo": "cerrado", "turno": None, "dia": dia})
                else:
                    turno = turno_map.get((dia, slot))
                    if turno:
                        tipo = "cancelada" if turno.cancelado else ("confirmada" if turno.aceptado else "pendiente")
                    else:
                        tipo = "libre"
                    row["celdas"].append({"tipo": tipo, "turno": turno, "dia": dia})
            grid.append(row)

        total      = turnos_semana.filter(cancelado=False).count()
        confirmadas = turnos_semana.filter(aceptado=True,  cancelado=False).count()
        pendientes  = turnos_semana.filter(aceptado=False, cancelado=False).count()
        canceladas  = turnos_semana.filter(cancelado=True).count()
        hoy         = timezone.localdate()

        context = {
            **self.admin_site.each_context(request),
            "title":         f"Semana {lunes.strftime('%d/%m')} – {domingo.strftime('%d/%m/%Y')}",
            "dias_semana":   dias_semana,
            "dias_nombres":  ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            "grid":          grid,
            "lunes":         lunes,
            "domingo":       domingo,
            "prev_semana":   lunes - datetime.timedelta(days=7),
            "next_semana":   lunes + datetime.timedelta(days=7),
            "hoy":           hoy,
            "total":         total,
            "confirmadas":   confirmadas,
            "pendientes":    pendientes,
            "canceladas":    canceladas,
        }
        return render(request, "admin/reservas/semana.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["agenda_url"] = "agenda/"
        extra_context["semana_url"] = "semana/"
        return super().changelist_view(request, extra_context=extra_context)


# ─── Configuración de agenda ──────────────────────────────────────────────────
@admin.register(ConfiguracionAgenda)
class ConfiguracionAgendaAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Horario de atención", {
            "fields": ("hora_inicio", "hora_fin", "intervalo_minutos"),
        }),
        ("Días laborables", {
            "fields": (
                "trabaja_lunes", "trabaja_martes", "trabaja_miercoles",
                "trabaja_jueves", "trabaja_viernes", "trabaja_sabado", "trabaja_domingo",
            ),
        }),
    )


@admin.register(DiaBloqueado)
class DiaBloqueadoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "motivo")
    ordering     = ("fecha",)
