# =============================================================================
# Context processor = función que envía datos a TODOS los templates.
# Aquí se arma el menú lateral según los permisos del usuario.
# =============================================================================
from collections import OrderedDict

from .crud import REGISTRO  # lista de todas las tablas con mantenedor

# Orden en que aparecen los grupos
ORDEN_GRUPOS = ["Operación", "Inventario", "Contratistas", "Mantenimiento", "Territorio", "Parametrización"]

# El menú lateral muestra solo lo del día a día; las tablas de parametrización
# (territorio, estados, tipos, reglas) se abren desde la entrada "Parametrización".
GRUPOS_MENU = ["Operación", "Inventario", "Contratistas", "Mantenimiento"]
FUERA_DEL_MENU = {"detalles-prestamo", "movimientos"}  # se ven dentro del préstamo y del activo


def navegacion(request):
    """Arma el menú lateral con los mantenedores que el usuario puede ver."""
    # Si no hay sesión iniciada no hay menú
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    grupos = OrderedDict((g, []) for g in ORDEN_GRUPOS)
    for m in sorted(REGISTRO.values(), key=lambda m: (m.orden, m.titulo)):
        # Solo se muestran las tablas que el rol del usuario puede VER
        if request.user.has_perm(m.perm("view")):
            grupos.setdefault(m.grupo, []).append(m)
    # Cantidad de alertas sin resolver (el número rojo de la campana)
    alertas = 0
    if request.user.has_perm("alertas.view_alerta"):
        from alertas.models import Alerta

        alertas = Alerta.objects.filter(resuelta=False).count()
    return {
        # Menú lateral (solo los grupos del día a día)
        "menu_grupos": [
            (g, [m for m in ms if m.slug not in FUERA_DEL_MENU])
            for g, ms in grupos.items() if g in GRUPOS_MENU and ms
        ],
        # Todas las tablas (para la página "Parametrización")
        "todos_grupos": [(g, ms) for g, ms in grupos.items() if ms],
        "alertas_pendientes": alertas,
        # Nombre del rol del usuario (se muestra en el menú de arriba a la derecha)
        "rol_usuario": ", ".join(request.user.groups.values_list("name", flat=True))
        or ("Superusuario" if request.user.is_superuser else "Sin rol"),
    }
