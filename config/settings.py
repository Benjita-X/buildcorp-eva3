"""
Configuración Django - BuildCorp (Sistema de Alquiler y Control de Herramientas).

Todos los valores sensibles o dependientes del entorno se leen desde variables
de entorno (archivo .env). Ver .env.example.
"""
# =============================================================================
# settings.py = el "panel de configuración" de todo el proyecto Django.
# Aquí se define: qué apps existen, a qué base de datos se conecta, la
# seguridad (login, sesiones), el idioma, los archivos estáticos y la API.
# =============================================================================
import os  # para leer variables de entorno (os.environ)
from pathlib import Path  # para armar rutas de carpetas

from dotenv import load_dotenv  # librería que lee el archivo .env

# BASE_DIR = la carpeta raíz del proyecto (donde está manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent
# Carga las variables del archivo .env (claves, base de datos, DEBUG...).
# Así las claves NO quedan escritas en el código ni se suben a GitHub.
load_dotenv(BASE_DIR / ".env")


# Lee una variable del .env y la convierte a True/False ("True", "1", "si" -> True)
def env_bool(nombre, defecto=False):
    return os.environ.get(nombre, str(defecto)).strip().lower() in ("1", "true", "yes", "si", "sí")


# Lee una variable del .env separada por comas y la convierte en lista
def env_list(nombre, defecto=""):
    return [x.strip() for x in os.environ.get(nombre, defecto).split(",") if x.strip()]


# Clave secreta de Django (firma sesiones y cookies). En el servidor viene del .env
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-inseguro-cambiar-en-produccion")
# DEBUG=True muestra errores detallados (solo para desarrollo). En el servidor es False
DEBUG = env_bool("DJANGO_DEBUG", True)
# Direcciones desde las que se puede abrir el sitio (en el servidor: la IP pública)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
# Orígenes confiables para los formularios (protección CSRF)
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

# Apps instaladas: Django solo "conoce" las apps que están en esta lista
INSTALLED_APPS = [
    # --- Apps que trae Django ---
    "django.contrib.admin",         # el Django Admin (/admin/)
    "django.contrib.auth",          # usuarios, grupos (roles) y permisos
    "django.contrib.contenttypes",
    "django.contrib.sessions",      # sesiones (mantener al usuario logueado)
    "django.contrib.messages",      # mensajes de éxito/error en pantalla
    "django.contrib.staticfiles",   # manejo de CSS y JavaScript
    "django.contrib.humanize",
    # Terceros
    "rest_framework",               # Django REST Framework (la API)
    "django_filters",               # filtros para la API
    # Apps del dominio
    "core",           # piezas compartidas: mantenedores, dashboard, API
    "parametros",     # región, ciudad, comuna, estados, tipos, reglas
    "inventario",     # obras, bodegas, activos y trazabilidad (Req. 1)
    "contratistas",   # contratistas y responsables de obra
    "prestamos",      # entrega y devolución con firma (Req. 2)
    "mantenimiento",  # planes preventivos y órdenes de trabajo (Req. 3)
    "alertas",        # morosidad y bloqueo automático (Req. 4)
    "usuarios",       # login, logout y gestión de usuarios con roles
]

# Middleware = "filtros" por los que pasa CADA petición antes de llegar a la vista
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",      # maneja la sesión
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",                 # protege los formularios (csrf_token)
    "django.contrib.auth.middleware.AuthenticationMiddleware",   # identifica al usuario logueado
    # Obliga a iniciar sesión en TODAS las vistas (LoginRequiredMiddleware de Django 5.1)
    "core.middleware.LoginObligatorioMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Archivo principal de URLs (la "recepción" que reparte las direcciones)
ROOT_URLCONF = "config.urls"

# Configuración de los templates (HTML)
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # carpeta donde están los HTML
        "APP_DIRS": True,
        "OPTIONS": {
            # Datos que se envían automáticamente a TODOS los templates
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",          # el usuario y sus permisos
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.navegacion",                   # el menú lateral
            ],
        },
    },
]

# Punto de entrada que usa Gunicorn en el servidor (config/wsgi.py)
WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Base de datos: PostgreSQL (requisito). DB_ENGINE=sqlite solo para pruebas locales.
# ---------------------------------------------------------------------------
if os.environ.get("DB_ENGINE", "postgres").lower() == "sqlite":
    # SQLite: un archivo local, solo para probar en el computador
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # PostgreSQL: la base de datos que se usa en el servidor de AWS.
    # Todos los datos de conexión se leen del archivo .env (no están en el código).
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",           # motor PostgreSQL
            "NAME": os.environ.get("DB_NAME", "buildcorp"),       # nombre de la base de datos
            "USER": os.environ.get("DB_USER", "buildcorp"),       # usuario de PostgreSQL
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),        # contraseña (desde el .env)
            "HOST": os.environ.get("DB_HOST", "localhost"),       # está en la misma máquina
            "PORT": os.environ.get("DB_PORT", "5432"),            # puerto de PostgreSQL
            "CONN_MAX_AGE": 60,                                   # reutiliza la conexión 60 segundos
        }
    }

# Reglas para las contraseñas de los usuarios (mínimo 8 caracteres, no muy comunes, etc.)
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Idioma español de Chile y hora de Santiago
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# Archivos estáticos (CSS, JavaScript, imágenes)
STATIC_URL = "static/"                     # URL con la que se piden: /static/...
STATICFILES_DIRS = [BASE_DIR / "static"]   # carpeta donde están en el proyecto
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic los junta aquí y Nginx los sirve en /static/

# Tipo de dato para los id automáticos de las tablas
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Autenticación y sesiones
# ---------------------------------------------------------------------------
LOGIN_URL = "usuarios:login"          # a dónde manda si no hay sesión iniciada
LOGIN_REDIRECT_URL = "dashboard"      # a dónde va después de iniciar sesión
LOGOUT_REDIRECT_URL = "usuarios:login"  # a dónde va después de cerrar sesión

# La sesión expira tras N segundos de inactividad (por defecto 30 min)
SESSION_COOKIE_AGE = int(os.environ.get("SESSION_COOKIE_AGE", 1800))
SESSION_SAVE_EVERY_REQUEST = True       # cada clic renueva los 30 minutos
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # al cerrar el navegador se cierra la sesión
SESSION_COOKIE_HTTPONLY = True          # JavaScript no puede leer la cookie de sesión (seguridad)
CSRF_COOKIE_HTTPONLY = False  # el JS de la firma/fetch lee el token desde el formulario


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # Formas de identificarse en la API: con la sesión del navegador o usuario/clave
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    # Para usar la API hay que estar logueado y tener el permiso del rol
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "core.permissions.PermisosModeloEstrictos",
    ],
    # Permite filtrar, buscar y ordenar en la API (?search=, ?ordering=)
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # La API muestra los resultados de a 20 por página
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Colores de Bootstrap para cada tipo de mensaje (info, éxito, advertencia, error)
MESSAGE_TAGS = {
    10: "secondary",  # debug
    20: "info",
    25: "success",
    30: "warning",
    40: "danger",
}

# Registro de eventos (logs): se muestran en la consola / journalctl del servidor
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
