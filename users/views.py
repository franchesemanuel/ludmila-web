from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.messages import get_messages
import re


# =========================
# VALIDACIÓN PASSWORD
# =========================
def validar_password(password):
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Z]", password):
        return "La contraseña debe tener al menos una letra mayúscula."
    if not re.search(r"\d", password):
        return "La contraseña debe tener al menos un número."
    return None


# =========================
# REGISTRO
# =========================
def register_view(request):
    # 🧹 limpiar mensajes arrastrados
    storage = get_messages(request)
    for _ in storage:
        pass

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        telefono = request.POST.get("telefono")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

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

        if User.objects.filter(username=telefono).exists():
            messages.error(request, "Ya existe una cuenta con ese teléfono.")
            return redirect("register")

        User.objects.create_user(
            username=telefono,
            password=password1,
            first_name=nombre
        )

        messages.success(request, "Cuenta creada correctamente. Ya podés iniciar sesión.")
        return redirect("login")

    return render(request, "users/register.html")


# =========================
# LOGIN
# =========================
def login_view(request):
    # 🧹 limpiar mensajes viejos
    storage = get_messages(request)
    for _ in storage:
        pass

    if request.method == "POST":
        telefono = request.POST.get("telefono")
        password = request.POST.get("password")

        user = authenticate(request, username=telefono, password=password)

        if user:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Teléfono o contraseña incorrectos.")
        return redirect("login")

    return render(request, "users/login.html")


# =========================
# LOGOUT
# =========================
def logout_view(request):
    logout(request)
    return redirect("home")


# =========================
# DASHBOARD
# =========================
def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect("login")

    from reservas.models import Turno

    turnos = Turno.objects.filter(
        telefono=request.user.username
    ).order_by("fecha", "hora")

    return render(
        request,
        "users/dashboard.html",
        {"turnos": turnos}
    )