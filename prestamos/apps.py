# Configuración de la app "prestamos" (nombre que se muestra en el Django Admin)
from django.apps import AppConfig


class PrestamosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prestamos"
    verbose_name = "Préstamos"
