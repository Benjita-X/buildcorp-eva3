from rest_framework.permissions import DjangoModelPermissions


class PermisosModeloEstrictos(DjangoModelPermissions):
    """Igual que DjangoModelPermissions pero también exige 'view' para leer (GET)."""

    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
    }
