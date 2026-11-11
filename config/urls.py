from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "BuildCorp · Administración"
admin.site.site_title = "BuildCorp Admin"
admin.site.index_title = "Panel de administración del sistema"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("usuarios/", include("usuarios.urls")),
    path("api/", include("core.api_urls")),
    path("prestamos/", include("prestamos.urls")),
    path("inventario/", include("inventario.urls")),
    path("contratistas/", include("contratistas.urls")),
    path("mantenimiento/", include("mantenimiento.urls")),
    path("alertas/", include("alertas.urls")),
    path("", include("core.urls")),
]
