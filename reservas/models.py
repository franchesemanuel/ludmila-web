from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import time, timedelta, datetime
from django.contrib.auth.models import User


# =====================
# VALIDADORES
# =====================

solo_letras = RegexValidator(
    regex=r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$',
    message="El nombre solo puede contener letras."
)

solo_numeros = RegexValidator(
    regex=r'^\d+$',
    message="El teléfono solo puede contener números."
)


# =====================
# CONFIGURACIÓN AGENDA
# =====================

class ConfiguracionAgenda(models.Model):
    hora_inicio = models.TimeField(default=time(9, 0))
    hora_fin = models.TimeField(default=time(18, 0))
    intervalo_minutos = models.PositiveIntegerField(default=30)

    trabaja_lunes = models.BooleanField(default=True)
    trabaja_martes = models.BooleanField(default=True)
    trabaja_miercoles = models.BooleanField(default=True)
    trabaja_jueves = models.BooleanField(default=True)
    trabaja_viernes = models.BooleanField(default=True)
    trabaja_sabado = models.BooleanField(default=False)
    trabaja_domingo = models.BooleanField(default=False)

    def __str__(self):
        return "Configuración de agenda"

    class Meta:
        verbose_name = "Configuración de agenda"
        verbose_name_plural = "Configuración de agenda"


# =====================
# DÍAS BLOQUEADOS
# =====================

class DiaBloqueado(models.Model):
    fecha = models.DateField(unique=True)
    motivo = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.fecha} - {self.motivo}"

    class Meta:
        verbose_name = "Día bloqueado"
        verbose_name_plural = "Días bloqueados"


# =====================
# TURNOS
# =====================

class Turno(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="turnos"
    )

    nombre_completo = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20)

    fecha = models.DateField()
    hora = models.TimeField()
    comentario = models.TextField(blank=True)

    aceptado = models.BooleanField(default=False)
    comentario_ludmila = models.TextField(
        blank=True,
        help_text="Comentario visible para el cliente"
    )

    creado = models.DateTimeField(auto_now_add=True)

    def puede_modificarse(self):
        fecha_hora = timezone.make_aware(
            timezone.datetime.combine(self.fecha, self.hora)
        )
        return fecha_hora - timezone.now() >= timedelta(hours=2)

    def __str__(self):
        return f"{self.nombre_completo} - {self.fecha} {self.hora}"
 
    # =====================
    # VALIDACIONES
    # =====================

    def clean(self):
        hoy = timezone.localdate()
        ahora = timezone.localtime().time()

        # ❌ Fecha pasada
        if self.fecha < hoy:
            raise ValidationError("No se pueden reservar fechas pasadas.")

        # ❌ Hora pasada si es hoy
        if self.fecha == hoy and self.hora <= ahora:
            raise ValidationError("No se pueden reservar horas pasadas.")

        # ❌ Día bloqueado
        if DiaBloqueado.objects.filter(fecha=self.fecha).exists():
            raise ValidationError("Este día no está disponible.")

        config = ConfiguracionAgenda.objects.first()
        if not config:
            raise ValidationError("La agenda no está configurada.")

        # ❌ Día no laboral
        dias = [
            config.trabaja_lunes,
            config.trabaja_martes,
            config.trabaja_miercoles,
            config.trabaja_jueves,
            config.trabaja_viernes,
            config.trabaja_sabado,
            config.trabaja_domingo,
        ]

        if not dias[self.fecha.weekday()]:
            raise ValidationError("No se atiende ese día.")

        # ❌ Fuera de horario
        if not (config.hora_inicio <= self.hora < config.hora_fin):
            raise ValidationError("Horario fuera de atención.")

        # ❌ Turno duplicado
        if Turno.objects.exclude(pk=self.pk).filter(
            fecha=self.fecha,
            hora=self.hora
        ).exists():
            raise ValidationError("Ese horario ya está reservado.")

    def save(self, *args, **kwargs):
        self.full_clean()  # 🔒 fuerza validaciones siempre
        super().save(*args, **kwargs)

    # =====================
    # LÓGICA DE NEGOCIO
    # =====================

    def puede_modificarse(self):
        """
        No se puede modificar con menos de 2 horas de anticipación
        """
        fecha_hora_turno = timezone.make_aware(
            datetime.combine(self.fecha, self.hora)
        )
        return fecha_hora_turno - timezone.now() >= timedelta(hours=2)

    def __str__(self):
        return f"{self.nombre_completo} - {self.fecha} {self.hora}"