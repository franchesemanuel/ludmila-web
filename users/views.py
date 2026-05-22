import logging
import re
import time

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.db import models
from django.shortcuts import render, redirect

logger = logging.getLogger("ludmila.security")

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60  # 15 minutos


def validar_password(password):
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Z]", password):
        return "La contraseña debe tener al menos una letra mayúscula."
    if not re.search(r"\d", password):
        return "La contraseña debe tener al menos un número."
    return None


def register_view(request):
    storage = get_messages(request)
    for _ in storage:
        pass

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$", nombre):
            messages.error(request, "El nombre solo puede contener letras.")
            return redirect("register")

        if not telefono.isdigit():
            messages.error(request, "El teléfono solo puede contener números.")
            return redirect("register")

        error = validar_password(password1)
        if error:
            messages.error(request, error)
            return redirect("register")

        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect("register")

        # Timing-neutral: no revelar si el teléfono ya existe
        if User.objects.filter(username=telefono).exists():
            messages.success(request, "Cuenta creada. Ya podés iniciar sesión.")
            return redirect("login")

        User.objects.create_user(
            username=telefono,
            password=password1,
            first_name=nombre,
        )

        logger.info("Nuevo usuario registrado: %s", telefono)
        messages.success(request, "Cuenta creada. Ya podés iniciar sesión.")
        return redirect("login")

    return render(request, "users/register.html")


def _get_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")


def login_view(request):
    storage = get_messages(request)
    for _ in storage:
        pass

    if request.method == "POST":
        telefono = request.POST.get("telefono", "").strip()
        password = request.POST.get("password", "")
        ip = _get_ip(request)
        cache_key = f"login_attempts:{ip}"

        attempts = cache.get(cache_key, 0)
        if attempts >= MAX_ATTEMPTS:
            logger.warning("Login bloqueado por rate-limit: IP=%s telefono=%s", ip, telefono)
            messages.error(request, "Demasiados intentos fallidos. Intentá de nuevo en 15 minutos.")
            return redirect("login")

        user = authenticate(request, username=telefono, password=password)

        if user:
            cache.delete(cache_key)
            login(request, user)
            logger.info("Login exitoso: usuario=%s IP=%s", telefono, ip)
            return redirect("home")

        cache.set(cache_key, attempts + 1, LOCKOUT_SECONDS)
        logger.warning("Login fallido: telefono=%s IP=%s intentos=%d", telefono, ip, attempts + 1)
        messages.error(request, "Teléfono o contraseña incorrectos.")
        return redirect("login")

    return render(request, "users/login.html")


def logout_view(request):
    logger.info("Logout: usuario=%s", request.user)
    logout(request)
    return redirect("home")


def mis_citas_view(request):
    if not request.user.is_authenticated:
        return redirect("login")

    from reservas.models import Turno
    from django.utils import timezone

    hoy = timezone.localdate()

    proximas = Turno.objects.filter(
        usuario=request.user,
        cancelado=False,
        fecha__gte=hoy,
    ).order_by("fecha", "hora")

    pasadas = Turno.objects.filter(
        usuario=request.user,
    ).filter(
        models.Q(fecha__lt=hoy) | models.Q(cancelado=True)
    ).order_by("-fecha", "-hora")

    return render(request, "users/mis_citas.html", {
        "proximas": proximas,
        "pasadas": pasadas,
    })
