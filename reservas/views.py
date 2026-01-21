from django.shortcuts import render, redirect
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib import messages
from .models import Turno, ConfiguracionAgenda, DiaBloqueado
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required






@login_required
def reservar(request):
    if request.method == "POST":

        # 👉 Si el usuario está logueado
        if request.user.is_authenticated:
            nombre = request.user.first_name
            telefono = request.user.username
            usuario = request.user
        else:
            nombre = request.POST.get("nombre_completo")
            telefono = request.POST.get("telefono")
            usuario = None

        Turno.objects.create(
            usuario=usuario,
            nombre_completo=nombre,
            telefono=telefono,
            fecha=request.POST.get("fecha"),
            hora=request.POST.get("hora"),
            comentario=request.POST.get("comentario", "")
        )

        messages.success(
            request,
            "✅ ¡Tu turno fue reservado con éxito!"
        )

        # 🔁 Redirección inteligente
        if request.user.is_authenticated:
            return redirect("dashboard")
        else:
            return redirect("reservar")

    return render(request, "reservas/reservar.html")


def horas_disponibles(request):
    fecha_str = request.GET.get("fecha")

    if not fecha_str:
        return JsonResponse({"horas": []})

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"horas": []})

    # ❌ día bloqueado
    if DiaBloqueado.objects.filter(fecha=fecha).exists():
        return JsonResponse({"horas": []})

    config = ConfiguracionAgenda.objects.first()
    if not config:
        return JsonResponse({"horas": []})

    # ❌ día no laborable
    dias = [
        config.trabaja_lunes,
        config.trabaja_martes,
        config.trabaja_miercoles,
        config.trabaja_jueves,
        config.trabaja_viernes,
        config.trabaja_sabado,
        config.trabaja_domingo,
    ]

    if not dias[fecha.weekday()]:
        return JsonResponse({"horas": []})

    hoy = timezone.localdate()
    ahora = timezone.localtime().time()

    ocupados = Turno.objects.filter(fecha=fecha).values_list("hora", flat=True)

    horas = []
    actual = datetime.combine(fecha, config.hora_inicio)
    fin = datetime.combine(fecha, config.hora_fin)

    while actual < fin:
        hora = actual.time()

        # ❌ horas pasadas si es hoy
        if fecha == hoy and hora <= ahora:
            actual += timedelta(minutes=config.intervalo_minutos)
            continue

        if hora not in ocupados:
            horas.append(hora.strftime("%H:%M"))

        actual += timedelta(minutes=config.intervalo_minutos)

    return JsonResponse({"horas": horas})


def editar_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id)

    # 🔒 Seguridad: solo el dueño del turno
    if str(turno.telefono) != request.user.username:
        messages.error(request, "No tenés permiso para editar este turno.")
        return redirect("dashboard")

    # ⏱ Regla: no editable con menos de 2 horas
    fecha_hora_turno = timezone.make_aware(
        datetime.combine(turno.fecha, turno.hora)
    )
    ahora = timezone.now()

    if fecha_hora_turno - ahora < timedelta(hours=2):
        messages.warning(
            request,
            "⏱ No podés modificar el turno con menos de 2 horas de anticipación."
        )
        return redirect("dashboard")

    if request.method == "POST":
        turno.fecha = request.POST.get("fecha")
        turno.hora = request.POST.get("hora")
        turno.comentario = request.POST.get("comentario", "")
        turno.aceptado = False  # vuelve a pendiente si se modifica
        turno.save()

        messages.success(request, "✅ Turno modificado correctamente.")
        return redirect("dashboard")

    return render(request, "reservas/editar_turno.html", {
        "turno": turno
    })