# =============================================================================
# wsgi.py = la "puerta de entrada" para el servidor de producción.
# Gunicorn (en AWS) carga "config.wsgi:application" para ejecutar Django.
# =============================================================================
import os

from django.core.wsgi import get_wsgi_application

# Indica qué archivo de configuración usar
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# Objeto que Gunicorn usa para atender las peticiones
application = get_wsgi_application()
