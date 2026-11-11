# Configuración de la app "parametros" (nombre que se muestra en el Django Admin)
from django.apps import AppConfig


class ParametrosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "parametros"
    verbose_name = "Parametrización"
