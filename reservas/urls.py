from django.urls import path
from . import views

urlpatterns = [
    path("", views.reservar, name="reservar"),
    path("horas-disponibles/", views.horas_disponibles, name="horas_disponibles"),
    path("dias-disponibles/", views.dias_disponibles, name="dias_disponibles"),
    path("cancelar/<int:turno_id>/", views.cancelar_turno, name="cancelar_turno"),
    path("staff/", views.staff_panel, name="staff_panel"),
    path("staff/cliente/<int:user_pk>/", views.staff_cliente_detalle, name="staff_cliente_detalle"),
]
