from django.db import migrations
from datetime import time


def crear_datos_iniciales(apps, schema_editor):
    Servicio = apps.get_model('reservas', 'Servicio')
    ConfiguracionAgenda = apps.get_model('reservas', 'ConfiguracionAgenda')

    # Crear agenda si no existe
    if not ConfiguracionAgenda.objects.exists():
        ConfiguracionAgenda.objects.create(
            hora_inicio=time(9, 0),
            hora_fin=time(18, 0),
            intervalo_minutos=30,
            trabaja_lunes=True,
            trabaja_martes=True,
            trabaja_miercoles=True,
            trabaja_jueves=True,
            trabaja_viernes=True,
            trabaja_sabado=True,
            trabaja_domingo=False,
        )

    # Crear servicios si no hay ninguno
    if not Servicio.objects.exists():
        pestanas = [
            ("Lifting de Pestañas", "Curva y levanta tus pestañas naturales. Dura hasta 8 semanas.", 60, 1),
            ("Extensiones pelo a pelo", "Volumen y largo natural con materiales premium.", 90, 2),
            ("Extensiones efecto volumen", "Máxima densidad con técnica de abanico ruso.", 120, 3),
            ("Tinte de Pestañas", "Color intenso y duradero sin necesidad de máscara.", 30, 4),
            ("Mantenimiento de extensiones", "Relleno cada 3 semanas para conservar el resultado.", 60, 5),
            ("Retiro de extensiones", "Retiro seguro sin daño con productos especializados.", 30, 6),
        ]
        for nombre, desc, dur, orden in pestanas:
            Servicio.objects.create(
                nombre=nombre,
                categoria='pestanas',
                descripcion=desc,
                duracion_minutos=dur,
                orden=orden,
                activo=True,
            )

        cejas = [
            ("Diseño de cejas", "Forma ideal según la estructura de tu rostro.", 30, 1),
            ("Laminado de cejas", "Efecto fullness y peinado que dura hasta 6 semanas.", 60, 2),
            ("Tinte de cejas", "Color uniforme y definición para cejas claras o con espacios.", 30, 3),
            ("Laminado + Tinte", "El combo definitivo: laminado y tinte en una sola sesión.", 75, 4),
            ("Henna de cejas", "Coloración natural que tine pelos y piel. Dura 4 semanas.", 45, 5),
            ("Combo Pestañas + Cejas", "Lifting de pestañas y laminado de cejas en una sesión.", 120, 6),
        ]
        for nombre, desc, dur, orden in cejas:
            Servicio.objects.create(
                nombre=nombre,
                categoria='cejas',
                descripcion=desc,
                duracion_minutos=dur,
                orden=orden,
                activo=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0009_servicio_categoria_y_datos_iniciales'),
    ]

    operations = [
        migrations.RunPython(crear_datos_iniciales, migrations.RunPython.noop),
    ]
