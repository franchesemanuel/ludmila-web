from django.urls import path
from . import views

urlpatterns = [
    path("", views.reservar, name="reservar"),
    path("horas-disponibles/", views.horas_disponibles, name="horas_disponibles"),
    path("editar/<int:turno_id>/", views.editar_turno, name="editar_turno"),
    path("editar/<int:turno_id>/", views.editar_turno, name="editar_turno"),
]