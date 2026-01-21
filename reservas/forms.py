from django import forms
from django.utils import timezone
from datetime import time
from .models import Turno

class TurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = [
            "nombre_completo",
            "telefono",
            "fecha",
            "hora",
            "comentario",
        ]
        widgets = {
            "nombre_completo": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre completo"
            }),
            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Número de teléfono"
            }),
            "fecha": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "hora": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time"
            }),
            "comentario": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Comentario (opcional)",
                "rows": 3
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get("fecha")
        hora = cleaned_data.get("hora")

        if not fecha or not hora:
            return cleaned_data

        # 1️⃣ No permitir fechas pasadas
        hoy = timezone.localdate()
        if fecha < hoy:
            raise forms.ValidationError("No se pueden reservar turnos en fechas pasadas.")

        # 2️⃣ No permitir domingos (weekday: lunes=0, domingo=6)
        if fecha.weekday() == 6:
            raise forms.ValidationError("No se atiende los domingos.")

        # 3️⃣ Horario laboral (09 a 18)
        hora_inicio = time(9, 0)
        hora_fin = time(18, 0)

        if not (hora_inicio <= hora <= hora_fin):
            raise forms.ValidationError("Horario disponible de 09:00 a 18:00.")

        # 4️⃣ Bloquear turnos duplicados
        if Turno.objects.filter(fecha=fecha, hora=hora).exists():
            raise forms.ValidationError("Ese horario ya está reservado. Elegí otro.")

        return cleaned_data