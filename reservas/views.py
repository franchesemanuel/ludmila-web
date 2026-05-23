import logging
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from datetime import datetime, timedelta, time as dtime, date
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from .models import Turno, ConfiguracionAgenda, HorarioBloque, DiaBloqueado, Servicio, MensajeCliente

_SAFE_BACK_RE = re.compile(r'^[?&=\w%-]+$')

logger = logging.getLogger("ludmila.security")

INTERVALO_DEFAULT = 30


def _get_intervalo():
    config = ConfiguracionAgenda.objects.first()
    return config.intervalo_minutos if config else INTERVALO_DEFAULT


def _bloques_para_dia(weekday: int):
    return list(HorarioBloque.objects.filter(dia=weekday, activo=True))


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

    bloques = _bloques_para_dia(fecha.weekday())
    if not bloques:
        return JsonResponse({"horas": [], "motivo": "dia_no_laboral"})

    intervalo = _get_intervalo()
    minimo_desde = timezone.now() + timedelta(hours=2)
    ocupados = set(
        Turno.objects.filter(fecha=fecha, cancelado=False).values_list("hora", flat=True)
    )

    slots_set = set()
    for bloque in bloques:
        actual = datetime.combine(fecha, bloque.hora_inicio)
        fin = datetime.combine(fecha, bloque.hora_fin)
        while actual < fin:
            hora = actual.time()
            slot_aware = timezone.make_aware(datetime.combine(fecha, hora))
            if slot_aware > minimo_desde and hora not in ocupados:
                slots_set.add(hora.strftime("%H:%M"))
            actual += timedelta(minutes=intervalo)

    horas = sorted(slots_set)
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
    dias_con_bloques = set(
        HorarioBloque.objects.filter(activo=True).values_list("dia", flat=True)
    )

    hoy = timezone.localdate()

    # flatpickr usa: 0=Dom, 1=Lun, 2=Mar, 3=Mie, 4=Jue, 5=Vie, 6=Sab
    python_a_fp = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}
    dias_semana_disabled = [
        python_a_fp[i] for i in range(7) if i not in dias_con_bloques
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


# ─── Panel staff unificado ────────────────────────────────────────────────────

DIAS_NOMBRES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
CATEGORIAS_VALIDAS = {"pestanas", "cejas"}


def _staff_required(view_fn):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not request.user.is_staff:
            return HttpResponseForbidden()
        return view_fn(request, *args, **kwargs)
    wrapped.__name__ = view_fn.__name__
    return wrapped


@_staff_required
def staff_panel(request):
    tab   = request.GET.get("tab", "agenda")
    fecha_str = request.GET.get("fecha")
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else timezone.localdate()
    except ValueError:
        fecha = timezone.localdate()

    if request.method == "POST":
        accion = request.POST.get("accion", "")
        _raw_back = request.POST.get("back", "")
        back = _raw_back if _SAFE_BACK_RE.match(_raw_back) else f"?tab={tab}&fecha={fecha}"

        try:
            if accion in ("confirmar", "cancelar", "pendiente"):
                turno = get_object_or_404(Turno, pk=request.POST.get("turno_id"))
                if accion == "confirmar":
                    Turno.objects.filter(pk=turno.pk).update(aceptado=True, cancelado=False)
                    messages.success(request, f"Cita de {turno.nombre_completo} confirmada.")
                elif accion == "cancelar":
                    Turno.objects.filter(pk=turno.pk).update(cancelado=True, aceptado=False)
                    messages.success(request, f"Cita de {turno.nombre_completo} cancelada.")
                elif accion == "pendiente":
                    Turno.objects.filter(pk=turno.pk).update(aceptado=False, cancelado=False)
                    messages.success(request, f"Cita de {turno.nombre_completo} puesta como pendiente.")

            elif accion == "crear_bloque":
                dia         = int(request.POST["dia"])
                hora_inicio = request.POST["hora_inicio"]
                hora_fin    = request.POST["hora_fin"]
                if hora_inicio >= hora_fin:
                    raise ValueError("La hora de inicio debe ser anterior a la de cierre.")
                HorarioBloque.objects.create(dia=dia, hora_inicio=hora_inicio, hora_fin=hora_fin)
                messages.success(request, f"Bloque {DIAS_NOMBRES[dia]} {hora_inicio}–{hora_fin} creado.")

            elif accion == "editar_bloque":
                bloque = get_object_or_404(HorarioBloque, pk=request.POST.get("bloque_id"))
                hora_inicio = request.POST["hora_inicio"]
                hora_fin    = request.POST["hora_fin"]
                if hora_inicio >= hora_fin:
                    raise ValueError("La hora de inicio debe ser anterior a la de cierre.")
                bloque.dia         = int(request.POST["dia"])
                bloque.hora_inicio = hora_inicio
                bloque.hora_fin    = hora_fin
                bloque.activo      = "activo" in request.POST
                bloque.save()
                messages.success(request, "Bloque actualizado.")

            elif accion == "eliminar_bloque":
                bloque = get_object_or_404(HorarioBloque, pk=request.POST.get("bloque_id"))
                bloque.delete()
                messages.success(request, "Bloque eliminado.")

            elif accion == "bloquear_dia":
                fecha_bloqueo = request.POST["fecha_bloqueo"]
                motivo = request.POST.get("motivo", "").strip()
                DiaBloqueado.objects.get_or_create(fecha=fecha_bloqueo, defaults={"motivo": motivo})
                messages.success(request, f"Día {fecha_bloqueo} bloqueado.")

            elif accion == "desbloquear_dia":
                DiaBloqueado.objects.filter(pk=request.POST.get("dia_id")).delete()
                messages.success(request, "Día desbloqueado.")

            elif accion == "guardar_config":
                intervalo = int(request.POST["intervalo_minutos"])
                if intervalo < 5 or intervalo > 240:
                    raise ValueError("El intervalo debe estar entre 5 y 240 minutos.")
                config, _ = ConfiguracionAgenda.objects.get_or_create(pk=1)
                config.intervalo_minutos = intervalo
                config.save()
                messages.success(request, f"Intervalo actualizado a {intervalo} minutos.")

            elif accion == "guardar_nota":
                turno = get_object_or_404(Turno, pk=request.POST.get("turno_id"))
                Turno.objects.filter(pk=turno.pk).update(
                    comentario_ludmila=request.POST.get("nota", "").strip()
                )
                messages.success(request, "Nota guardada.")

            elif accion == "crear_servicio":
                categoria = request.POST.get("categoria", "pestanas")
                if categoria not in CATEGORIAS_VALIDAS:
                    raise ValueError("Categoría inválida.")
                Servicio.objects.create(
                    nombre=request.POST["nombre"],
                    categoria=categoria,
                    descripcion=request.POST.get("descripcion", ""),
                    duracion_minutos=int(request.POST.get("duracion_minutos", 60)),
                    precio=request.POST.get("precio") or None,
                    activo="activo" in request.POST,
                    orden=int(request.POST.get("orden", 0)),
                )
                messages.success(request, "Servicio creado.")

            elif accion == "editar_servicio":
                categoria = request.POST.get("categoria", "pestanas")
                if categoria not in CATEGORIAS_VALIDAS:
                    raise ValueError("Categoría inválida.")
                s = get_object_or_404(Servicio, pk=request.POST.get("servicio_id"))
                s.nombre            = request.POST["nombre"]
                s.categoria         = categoria
                s.descripcion       = request.POST.get("descripcion", "")
                s.duracion_minutos  = int(request.POST.get("duracion_minutos", 60))
                s.precio            = request.POST.get("precio") or None
                s.activo            = "activo" in request.POST
                s.orden             = int(request.POST.get("orden", 0))
                s.save()
                messages.success(request, "Servicio actualizado.")

            elif accion == "eliminar_servicio":
                get_object_or_404(Servicio, pk=request.POST.get("servicio_id")).delete()
                messages.success(request, "Servicio eliminado.")

        except (ValueError, KeyError) as e:
            messages.error(request, str(e))

        return redirect(f"/reservar/staff/{back}")

    # ── GET ──────────────────────────────────────────────────────────────────
    turnos = (
        Turno.objects
        .filter(fecha=fecha)
        .select_related("servicio", "usuario")
        .order_by("hora")
    )
    hoy = timezone.localdate()

    return render(request, "reservas/staff_panel.html", {
        "tab":             tab,
        "fecha":           fecha,
        "prev_fecha":      fecha - timedelta(days=1),
        "next_fecha":      fecha + timedelta(days=1),
        "hoy":             hoy,
        "turnos":          turnos,
        "total":           turnos.filter(cancelado=False).count(),
        "confirmadas":     turnos.filter(aceptado=True,  cancelado=False).count(),
        "pendientes":      turnos.filter(aceptado=False, cancelado=False).count(),
        "canceladas":      turnos.filter(cancelado=True).count(),
        "bloques":         HorarioBloque.objects.all(),
        "dias_bloqueados": DiaBloqueado.objects.filter(fecha__gte=hoy).order_by("fecha"),
        "config":          ConfiguracionAgenda.objects.first(),
        "dias_semana":     list(enumerate(DIAS_NOMBRES)),
        "servicios":       Servicio.objects.all(),
        "clientes":        User.objects.filter(is_staff=False).order_by("first_name"),
        "categorias":      [("pestanas", "Pestañas"), ("cejas", "Cejas")],
    })


# ── Ficha de cliente ──────────────────────────────────────────────────────────

@_staff_required
def staff_cliente_detalle(request, user_pk):
    cliente = get_object_or_404(User, pk=user_pk, is_staff=False, is_superuser=False)

    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "enviar_mensaje":
            texto = request.POST.get("mensaje", "").strip()
            if texto:
                MensajeCliente.objects.create(usuario=cliente, es_staff=True, texto=texto)
                messages.success(request, "Mensaje enviado.")

        elif accion == "guardar_nota":
            turno = get_object_or_404(Turno, pk=request.POST.get("turno_id"), usuario=cliente)
            Turno.objects.filter(pk=turno.pk).update(
                comentario_ludmila=request.POST.get("nota", "").strip()
            )
            messages.success(request, "Nota guardada.")

        return redirect("staff_cliente_detalle", user_pk=user_pk)

    hoy = timezone.localdate()
    turnos   = Turno.objects.filter(usuario=cliente).select_related("servicio").order_by("-fecha", "-hora")
    mensajes = MensajeCliente.objects.filter(usuario=cliente)
    MensajeCliente.objects.filter(usuario=cliente, es_staff=False, leido=False).update(leido=True)

    return render(request, "reservas/staff_cliente.html", {
        "cliente":  cliente,
        "turnos":   turnos,
        "mensajes": mensajes,
        "hoy":      hoy,
    })
