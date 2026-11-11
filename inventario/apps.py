# Configuración de la app "inventario" (nombre que se muestra en el Django Admin)
from django.apps import AppConfig


class InventarioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventario"
    verbose_name = "Inventario de activos"
