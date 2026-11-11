from core.crud import Mantenedor, registrar
from parametros.models import EstadoMantenimiento

from .models import Mantenimiento, PlanMantenimiento


def _ot_antes_de_guardar(obj, request, creando):
    if creando:
        obj.estado = EstadoMantenimiento.por_codigo(EstadoMantenimiento.PROGRAMADA)
        obj.creado_por = request.user


registrar(Mantenedor(
    PlanMantenimiento, "planes", "Mantenimiento", "bi-calendar-check", orden=1,
    titulo="Planes preventivos",
    columnas=["activo", "descripcion", "tipo", "cada_horas", "cada_dias", "ultima_fecha", "vigente"],
    busqueda=["activo__codigo", "activo__nombre", "descripcion"], filtros=["tipo", "vigente"],
    ayuda="Defina cada cuántas horas de uso y/o días se debe mantener un activo. Al vencer se genera la OT automáticamente.",
))
registrar(Mantenedor(
    Mantenimiento, "mantenimientos", "Mantenimiento", "bi-gear-wide-connected", orden=2,
    titulo="Órdenes de trabajo",
    columnas=["folio", "activo", "tipo", "estado", "fecha_programada", "tecnico", "costo"],
    busqueda=["activo__codigo", "activo__nombre", "tecnico", "descripcion"], filtros=["estado", "tipo"],
    campos=["activo", "tipo", "fecha_programada", "tecnico", "descripcion"],
    queryset=lambda r: Mantenimiento.objects.select_related("activo", "tipo", "estado"),
    antes_de_guardar=_ot_antes_de_guardar, url_detalle="mantenimiento:detalle",
    permite_eliminar=False,
))
