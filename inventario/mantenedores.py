# Pantallas de administración (mantenedores con templates) de la app inventario
from core.crud import Mantenedor, registrar
from parametros.models import EstadoActivo

from .models import Activo, Bodega, MovimientoActivo, Obra


# Antes de guardar un activo nuevo: siempre ingresa como "Disponible"
def _activo_antes_de_guardar(obj, request, creando):
    # Un activo nuevo siempre ingresa como Disponible
    if creando and not obj.estado_id:
        obj.estado = EstadoActivo.por_codigo(EstadoActivo.DISPONIBLE)


# /m/activos/ (el estado NO se edita aquí: cambia con los flujos para que quede la trazabilidad)
registrar(Mantenedor(
    Activo, "activos", "Inventario", "bi-tools", orden=1,
    titulo="Activos y herramientas",
    columnas=["codigo", "nombre", "categoria", "marca", "estado", "bodega", "horas_uso", "tarifa_diaria"],
    busqueda=["codigo", "nombre", "modelo", "numero_serie", "marca__nombre"],
    filtros=["estado", "categoria", "bodega", "marca"],
    campos=["codigo", "nombre", "categoria", "marca", "modelo", "numero_serie", "bodega",
            "tarifa_diaria", "valor_compra", "fecha_adquisicion", "horas_uso", "observaciones"],
    antes_de_guardar=_activo_antes_de_guardar,
    url_detalle="inventario:activo_detalle",  # al abrir un activo se ve su hoja de vida
    ayuda="El estado se cambia con los flujos (préstamo, devolución, mantención, baja), así queda la trazabilidad.",
))
# /m/bodegas/
registrar(Mantenedor(
    Bodega, "bodegas", "Inventario", "bi-box-seam", orden=2,
    columnas=["nombre", "obra", "comuna", "encargado", "vigente"],
    busqueda=["nombre", "direccion", "comuna__nombre"], filtros=["obra", "vigente"],
))
# /m/obras/
registrar(Mantenedor(
    Obra, "obras", "Inventario", "bi-cone-striped", orden=3,
    columnas=["codigo", "nombre", "comuna", "jefe_obra", "fecha_inicio", "vigente"],
    busqueda=["codigo", "nombre", "jefe_obra"], filtros=["vigente"],
))
# /m/movimientos/ : solo lectura (los movimientos se crean solos y no se pueden alterar)
registrar(Mantenedor(
    MovimientoActivo, "movimientos", "Inventario", "bi-arrow-left-right", orden=4,
    titulo="Trazabilidad (movimientos)",
    columnas=["fecha", "activo", "estado_anterior", "estado_nuevo", "bodega_origen", "bodega_destino", "usuario", "descripcion"],
    busqueda=["activo__codigo", "activo__nombre", "descripcion"], filtros=["estado_nuevo", "bodega_destino"],
    permite_crear=False, permite_editar=False, permite_eliminar=False,
    ayuda="Registro automático e inalterable de cada cambio de estado o bodega.",
))
