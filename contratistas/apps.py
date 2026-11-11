# Configuración de la app "contratistas" (nombre que se muestra en el Django Admin)
from django.apps import AppConfig


class ContratistasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contratistas"
    verbose_name = "Contratistas"
