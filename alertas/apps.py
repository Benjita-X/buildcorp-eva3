# Configuración de la app "alertas" (nombre que se muestra en el Django Admin)
from django.apps import AppConfig


class AlertasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "alertas"
    verbose_name = "Alertas"
