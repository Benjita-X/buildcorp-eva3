# URLs de la app contratistas (empiezan con /contratistas/)
from django.urls import path

from . import views

app_name = "contratistas"
urlpatterns = [
    path("<int:pk>/", views.detalle, name="detalle"),                  # ficha del contratista
    path("<int:pk>/bloquear/", views.bloquear, name="bloquear"),       # bloqueo manual
    path("<int:pk>/desbloquear/", views.desbloquear, name="desbloquear"),  # desbloqueo manual
]
