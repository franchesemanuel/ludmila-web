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
# SERVICIOS
# =====================

CATEGORIA_CHOICES = [
    ('pestanas', 'Pestañas'),
    ('cejas', 'Cejas'),
]

class Servicio(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='pestanas')
    descripcion = models.TextField(blank=True)
    duracion_minutos = models.PositiveIntegerField(default=60)
    precio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ["categoria", "orden", "nombre"]


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
    comentario = models.TextField(blank=True, max_length=500)

    servicio = models.ForeignKey('Servicio', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Servicio")
    cancelado = models.BooleanField(default=False)

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
        import datetime as _dt

        # ── Asegurar tipos correctos (el POST envía strings) ──────────────────
        try:
            fecha = self.fecha if isinstance(self.fecha, _dt.date) else _dt.date.fromisoformat(str(self.fecha))
            hora  = self.hora  if isinstance(self.hora,  _dt.time) else _dt.time.fromisoformat(str(self.hora)[:5])
        except (ValueError, TypeError, AttributeError):
            raise ValidationError("Fecha u hora inválida.")

        # ── Sólo para turnos NUEVOS: validar que no sea hora pasada ───────────
        # Los turnos existentes (admin confirmando, editando nota, etc.) no
        # se revalidan para no bloquear la gestión de citas ya creadas.
        if not self.pk:
            slot_aware = timezone.make_aware(_dt.datetime.combine(fecha, hora))
            if slot_aware <= timezone.now() + _dt.timedelta(hours=2):
                raise ValidationError("Las reservas requieren al menos 2 horas de anticipación.")

            # Día bloqueado
            if DiaBloqueado.objects.filter(fecha=fecha).exists():
                raise ValidationError("Este día no está disponible.")

            config = ConfiguracionAgenda.objects.first()
            if not config:
                raise ValidationError("La agenda no está configurada.")

            dias = [
                config.trabaja_lunes, config.trabaja_martes, config.trabaja_miercoles,
                config.trabaja_jueves, config.trabaja_viernes,
                config.trabaja_sabado, config.trabaja_domingo,
            ]
            if not dias[fecha.weekday()]:
                raise ValidationError("No se atiende ese día.")

            if not (config.hora_inicio <= hora < config.hora_fin):
                raise ValidationError("Horario fuera de atención.")

        # ── Siempre: no superponer con otro turno activo ──────────────────────
        if Turno.objects.exclude(pk=self.pk).filter(
            fecha=self.fecha, hora=self.hora, cancelado=False
        ).exists():
            raise ValidationError("Ese horario ya está reservado.")

    def save(self, *args, **kwargs):
        self.full_clean()  # 🔒 fuerza validaciones siempre
        super().save(*args, **kwargs)

    # =====================
    # LÓGICA DE NEGOCIO
    # =====================

    def puede_modificarse(self):
        fecha_hora_turno = timezone.make_aware(
            datetime.combine(self.fecha, self.hora)
        )
        return fecha_hora_turno - timezone.now() >= timedelta(hours=2)

    def __str__(self):
        return f"{self.nombre_completo} - {self.fecha} {self.hora}"

    class Meta:
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"
        constraints = [
            models.UniqueConstraint(
                fields=["fecha", "hora"],
                condition=models.Q(cancelado=False),
                name="unique_turno_activo_por_slot",
            )
        ]