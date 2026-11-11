# =============================================================================
# Permisos de la API: cada petición revisa el permiso del rol del usuario.
# =============================================================================
from rest_framework.permissions import DjangoModelPermissions


# DjangoModelPermissions revisa los permisos de Django (add, change, delete).
# Esta versión además exige el permiso "view" para poder LEER (GET).
class PermisosModeloEstrictos(DjangoModelPermissions):
    """Igual que DjangoModelPermissions pero también exige 'view' para leer (GET)."""

    perms_map = {
        **DjangoModelPermissions.perms_map,                  # POST=add, PUT/PATCH=change, DELETE=delete
        "GET": ["%(app_label)s.view_%(model_name)s"],        # leer exige permiso "view"
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
    }
