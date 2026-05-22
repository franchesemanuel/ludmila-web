import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from datetime import datetime, timedelta, time as dtime, date
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from .models import Turno, ConfiguracionAgenda, DiaBloqueado, Servicio

logger = logging.getLogger("ludmila.security")

HORA_INICIO_DEFAULT = dtime(9, 0)
HORA_FIN_DEFAULT = dtime(18, 0)
INTERVALO_DEFAULT = 30
DIAS_DEFAULT = [True, True, True, True, True, True, False]  # Lun-Sab, Dom no


def _get_config():
    config = ConfiguracionAgenda.objects.first()
    if config:
        return (
            config.hora_inicio,
            config.hora_fin,
            config.intervalo_minutos,
            [
                config.trabaja_lunes, config.trabaja_martes,
                config.trabaja_miercoles, config.trabaja_jueves,
                config.trabaja_viernes, config.trabaja_sabado,
                config.trabaja_domingo,
            ]
        )
    return HORA_INICIO_DEFAULT, HORA_FIN_DEFAULT, INTERVALO_DEFAULT, DIAS_DEFAULT


@login_required
def reservar(request):
    servicios_pestanas = Servicio.objects.filter(activo=True, categoria='pestanas')
    servicios_cejas    = Servicio.objects.filter(activo=True, categoria='cejas')
    ctx = {"servicios_pestanas": servicios_pestanas, "servicios_cejas": servicios_cejas}

    if request.method == "POST":

        # ── 1. Parsear tipos correctos desde el POST ──────────────────────────
        fecha_str = request.POST.get("fecha", "").strip()
        hora_str  = request.POST.get("hora",  "").strip()

        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Fecha inválida. Usá el calendario.")
            return render(request, "reservas/reservar.html", ctx)

        try:
            hora = datetime.strptime(hora_str, "%H:%M").time()
        except ValueError:
            messages.error(request, "Hora inválida. Seleccioná un horario disponible.")
            return render(request, "reservas/reservar.html", ctx)

        # ── 2. Verificar mínimo 2 horas de anticipación ───────────────────────
        slot_aware = timezone.make_aware(datetime.combine(fecha, hora))
        if slot_aware <= timezone.now() + timedelta(hours=2):
            messages.error(request, "Las reservas requieren al menos 2 horas de anticipación.")
            return render(request, "reservas/reservar.html", ctx)

        # ── 3. Verificar que el slot no esté ocupado ──────────────────────────
        if Turno.objects.filter(fecha=fecha, hora=hora, cancelado=False).exists():
            messages.error(request, "Ese horario ya está reservado. Por favor elegí otro.")
            return render(request, "reservas/reservar.html", ctx)

        # ── 4. Verificar que el usuario no tenga ya una cita ese día ─────────
        if Turno.objects.filter(usuario=request.user, fecha=fecha, cancelado=False).exists():
            messages.error(request, "Ya tenés una cita reservada para ese día.")
            return render(request, "reservas/reservar.html", ctx)

        # ── 5. Resolver servicio ──────────────────────────────────────────────
        servicio = None
        servicio_id = request.POST.get("servicio")
        if servicio_id:
            try:
                servicio = Servicio.objects.get(id=servicio_id, activo=True)
            except Servicio.DoesNotExist:
                pass

        # ── 6. Crear — el modelo todavía corre full_clean() como última red ───
        try:
            Turno.objects.create(
                usuario=request.user,
                nombre_completo=request.user.first_name or request.user.username,
                telefono=request.user.username,
                fecha=fecha,
                hora=hora,
                comentario=request.POST.get("comentario", "")[:500],
                servicio=servicio,
            )
            logger.info(
                "Reserva creada: usuario=%s fecha=%s hora=%s servicio=%s",
                request.user.username, fecha, hora,
                servicio.nombre if servicio else "—",
            )
            messages.success(request, "Tu cita fue reservada. Te confirmamos a la brevedad.")
            return redirect("mis_citas")
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)

    return render(request, "reservas/reservar.html", ctx)


@login_required
def horas_disponibles(request):
    """
    Devuelve lista de horas disponibles para una fecha dada.
    Usa comparación timezone-aware para filtrar horas pasadas.
    """
    fecha_str = request.GET.get("fecha")
    if not fecha_str:
        return JsonResponse({"horas": []})

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"horas": []})

    # Fecha en el pasado
    if fecha < timezone.localdate():
        return JsonResponse({"horas": [], "motivo": "fecha_pasada"})

    if DiaBloqueado.objects.filter(fecha=fecha).exists():
        return JsonResponse({"horas": [], "motivo": "dia_bloqueado"})

    hora_inicio, hora_fin, intervalo, dias = _get_config()

    if not dias[fecha.weekday()]:
        return JsonResponse({"horas": [], "motivo": "dia_no_laboral"})

    # Límite: el slot debe estar al menos 2 horas en el futuro
    minimo_desde = timezone.now() + timedelta(hours=2)

    ocupados = set(
        Turno.objects.filter(fecha=fecha, cancelado=False).values_list("hora", flat=True)
    )

    horas = []
    actual = datetime.combine(fecha, hora_inicio)
    fin = datetime.combine(fecha, hora_fin)

    while actual < fin:
        hora = actual.time()
        slot_aware = timezone.make_aware(datetime.combine(fecha, hora))
        if slot_aware > minimo_desde and hora not in ocupados:
            horas.append(hora.strftime("%H:%M"))
        actual += timedelta(minutes=intervalo)

    response = JsonResponse({"horas": horas})
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


@login_required
def dias_disponibles(request):
    """
    Devuelve los días deshabilitados para los próximos 90 días:
    - Fechas específicas bloqueadas (DiaBloqueado)
    - Días de la semana no laborables
    """
    _, _, _, dias = _get_config()

    hoy = timezone.localdate()

    # flatpickr usa: 0=Dom, 1=Lun, 2=Mar, 3=Mie, 4=Jue, 5=Vie, 6=Sab
    python_a_fp = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}
    dias_semana_disabled = [
        python_a_fp[i] for i, trabaja in enumerate(dias) if not trabaja
    ]

    hasta = hoy + timedelta(days=90)
    fechas_bloqueadas = list(
        DiaBloqueado.objects.filter(fecha__gte=hoy, fecha__lte=hasta)
        .values_list("fecha", flat=True)
    )
    fechas_bloqueadas_str = [f.strftime("%Y-%m-%d") for f in fechas_bloqueadas]

    return JsonResponse({
        "dias_semana_disabled": dias_semana_disabled,
        "fechas_bloqueadas": fechas_bloqueadas_str,
        "hoy": hoy.strftime("%Y-%m-%d"),
    })


@login_required
def cancelar_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id, usuario=request.user)

    if not turno.puede_modificarse():
        messages.warning(request, "No podés cancelar con menos de 2 horas de anticipación.")
        return redirect("mis_citas")

    if request.method == "POST":
        Turno.objects.filter(pk=turno.pk).update(cancelado=True, aceptado=False)
        logger.info(
            "Turno cancelado: usuario=%s turno_id=%d fecha=%s hora=%s",
            request.user.username, turno.pk, turno.fecha, turno.hora,
        )
        messages.success(request, "Cita cancelada correctamente.")
        return redirect("mis_citas")

    return render(request, "reservas/cancelar_turno.html", {"turno": turno})
