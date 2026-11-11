# Pantallas de administración (mantenedores con templates) de la app préstamos
from django.db.models import F
from django.urls import reverse

from core.crud import Mantenedor, registrar

from .models import DetallePrestamo, Prestamo


# Botón verde "Devolver" en la fila de cada préstamo pendiente (si el usuario tiene permiso)
def _acciones_prestamo(prestamo, usuario):
    """Botón 'Devolver' directo en la fila de los préstamos pendientes."""
    if prestamo.abierto and usuario.has_perm("prestamos.change_prestamo"):
        return [{"url": reverse("prestamos:devolver", args=[prestamo.pk]), "texto": "Devolver",
                 "icono": "bi-box-arrow-in-down-left", "color": "success", "titulo": "Registrar devolución"}]
    return []

registrar(Mantenedor(
    Prestamo, "prestamos", "Operación", "bi-box-arrow-up-right", orden=1,
    titulo="Préstamos (entregas)",
    columnas=["folio", "contratista", "obra", "fecha_entrega", "fecha_compromiso", "estado", "fecha_devolucion"],
    busqueda=["contratista__razon_social", "contratista__rut", "obra__codigo", "obra__nombre", "responsable__nombre"],
    filtros=["estado", "contratista", "obra"],
    # Primero los pendientes de devolución, después los devueltos
    queryset=lambda r: Prestamo.objects.select_related("contratista", "obra", "estado")
    .order_by(F("fecha_devolucion").asc(nulls_first=True), "-fecha_entrega"),
    acciones=_acciones_prestamo,
    url_crear="prestamos:nuevo", url_detalle="prestamos:detalle",
    permite_editar=False, permite_eliminar=False,
    ayuda="Las entregas y devoluciones se registran con firma digital del responsable de obra.",
))
registrar(Mantenedor(
    DetallePrestamo, "detalles-prestamo", "Operación", "bi-list-check", orden=2,
    titulo="Detalle de préstamos",
    columnas=["prestamo", "activo", "bodega_origen", "tarifa_diaria", "horas_uso", "condicion", "devuelto"],
    busqueda=["activo__codigo", "activo__nombre", "prestamo__contratista__razon_social"],
    filtros=["devuelto", "condicion", "bodega_origen"],
    queryset=lambda r: DetallePrestamo.objects.select_related("prestamo__contratista", "activo", "bodega_origen", "condicion"),
    permite_crear=False, permite_editar=False, permite_eliminar=False,
    ayuda="Herramientas de cada préstamo. Se generan al registrar la entrega y se completan en la devolución.",
))
