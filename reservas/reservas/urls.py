from django.urls import path
from .views import reservar

urlpatterns = [
    path("", reservar, name="reservar"),
]