# Configuración de la app "core" (las piezas compartidas del sistema)
from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Núcleo"

    # ready() se ejecuta cuando Django termina de arrancar
    def ready(self):
        # Carga el archivo mantenedores.py de cada app (registro de pantallas CRUD)
        autodiscover_modules("mantenedores")
