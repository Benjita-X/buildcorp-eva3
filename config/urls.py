# =============================================================================
# urls.py principal = la "recepción" del sitio.
# Recibe cada dirección (URL) y la manda a la app que corresponde.
# Ejemplo: /prestamos/nuevo/ -> va a prestamos/urls.py
# =============================================================================
from django.contrib import admin
from django.urls import include, path

# Textos que se ven arriba en el Django Admin
admin.site.site_header = "BuildCorp · Administración"
admin.site.site_title = "BuildCorp Admin"
admin.site.index_title = "Panel de administración del sistema"

urlpatterns = [
    path("admin/", admin.site.urls),                      # Django Admin
    path("usuarios/", include("usuarios.urls")),          # login, logout, gestión de usuarios
    path("api/", include("core.api_urls")),               # API REST (Django REST Framework)
    path("prestamos/", include("prestamos.urls")),        # entregas y devoluciones
    path("inventario/", include("inventario.urls")),      # hoja de vida, traslado y baja de activos
    path("contratistas/", include("contratistas.urls")),  # ficha del contratista
    path("mantenimiento/", include("mantenimiento.urls")),  # órdenes de trabajo
    path("alertas/", include("alertas.urls")),            # lista de alertas
    path("", include("core.urls")),                       # dashboard y mantenedores de cada tabla
]
