from collections import OrderedDict

from .crud import REGISTRO

ORDEN_GRUPOS = ["Operación", "Inventario", "Contratistas", "Mantenimiento", "Territorio", "Parametrización"]


def navegacion(request):
    """Arma el menú lateral con los mantenedores que el usuario puede ver."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    grupos = OrderedDict((g, []) for g in ORDEN_GRUPOS)
    for m in sorted(REGISTRO.values(), key=lambda m: (m.orden, m.titulo)):
        if request.user.has_perm(m.perm("view")):
            grupos.setdefault(m.grupo, []).append(m)
    alertas = 0
    if request.user.has_perm("alertas.view_alerta"):
        from alertas.models import Alerta

        alertas = Alerta.objects.filter(resuelta=False).count()
    return {
        "menu_grupos": [(g, ms) for g, ms in grupos.items() if ms],
        "alertas_pendientes": alertas,
        "rol_usuario": ", ".join(request.user.groups.values_list("name", flat=True))
        or ("Superusuario" if request.user.is_superuser else "Sin rol"),
    }
