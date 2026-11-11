# Configuración de la app "usuarios" (nombre que se muestra en el Django Admin)
from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"
    verbose_name = "Usuarios"
