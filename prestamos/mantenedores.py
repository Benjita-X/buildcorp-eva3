from core.crud import Mantenedor, registrar

from .models import Prestamo

registrar(Mantenedor(
    Prestamo, "prestamos", "Operación", "bi-box-arrow-up-right", orden=1,
    titulo="Préstamos (entregas)",
    columnas=["folio", "contratista", "obra", "fecha_entrega", "fecha_compromiso", "estado", "fecha_devolucion"],
    busqueda=["contratista__razon_social", "contratista__rut", "obra__codigo", "obra__nombre", "responsable__nombre"],
    filtros=["estado", "contratista", "obra"],
    queryset=lambda r: Prestamo.objects.select_related("contratista", "obra", "estado"),
    url_crear="prestamos:nuevo", url_detalle="prestamos:detalle",
    permite_editar=False, permite_eliminar=False,
    ayuda="Las entregas y devoluciones se registran con firma digital del responsable de obra.",
))
