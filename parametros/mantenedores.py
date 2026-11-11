"""Registro de los mantenedores (pantallas CRUD por template) de las tablas de parametrización."""
# Cada registrar(Mantenedor(...)) crea la pantalla de administración de una tabla:
#   modelo, slug (nombre en la URL), grupo del menú, ícono,
#   columnas (qué se ve), busqueda (en qué campos busca), filtros (listas desplegables)
#   y campos (qué se puede editar en el formulario).
from core.crud import Mantenedor, registrar

from . import models as m

# ---------------- Territorio ----------------
# /m/regiones/
registrar(Mantenedor(
    m.Region, "regiones", "Territorio", "bi-map", orden=1,
    columnas=["codigo", "nombre", "orden", "vigente"], busqueda=["codigo", "nombre"], filtros=["vigente"],
))
# /m/ciudades/ (se puede filtrar por región)
registrar(Mantenedor(
    m.Ciudad, "ciudades", "Territorio", "bi-buildings", orden=2,
    columnas=["nombre", "region", "vigente"], busqueda=["nombre", "region__nombre"], filtros=["region", "vigente"],
))
# /m/comunas/ (muestra también la región de la comuna con "ciudad__region")
registrar(Mantenedor(
    m.Comuna, "comunas", "Territorio", "bi-geo-alt", orden=3,
    columnas=["nombre", "ciudad", "ciudad__region", "vigente"],
    busqueda=["nombre", "ciudad__nombre", "ciudad__region__nombre"], filtros=["ciudad", "vigente"],
    queryset=lambda r: m.Comuna.objects.select_related("ciudad__region"),
))

# ---------------- Catálogos ----------------
registrar(Mantenedor(
    m.CategoriaActivo, "categorias", "Parametrización", "bi-tags", orden=10,
    columnas=["nombre", "descripcion", "vigente"], busqueda=["nombre"], filtros=["vigente"],
))
registrar(Mantenedor(
    m.Marca, "marcas", "Parametrización", "bi-award", orden=11,
    columnas=["nombre", "vigente"], busqueda=["nombre"], filtros=["vigente"],
))
registrar(Mantenedor(
    m.Cargo, "cargos", "Parametrización", "bi-person-badge", orden=12,
    columnas=["nombre", "vigente"], busqueda=["nombre"], filtros=["vigente"],
))

# ---------------- Estados y tipos ----------------
# Campos comunes que se pueden editar en todos los estados y tipos
_cod = ["codigo", "nombre", "color", "orden", "vigente"]
registrar(Mantenedor(
    m.EstadoActivo, "estados-activo", "Parametrización", "bi-toggles", orden=20,
    columnas=["nombre", "codigo", "permite_prestamo", "es_sistema", "vigente"], busqueda=["nombre", "codigo"],
    campos=_cod + ["permite_prestamo"],
))
registrar(Mantenedor(
    m.EstadoPrestamo, "estados-prestamo", "Parametrización", "bi-toggles", orden=21,
    columnas=["nombre", "codigo", "es_sistema", "vigente"], busqueda=["nombre", "codigo"], campos=_cod,
))
registrar(Mantenedor(
    m.EstadoMantenimiento, "estados-mantenimiento", "Parametrización", "bi-toggles", orden=22,
    columnas=["nombre", "codigo", "es_sistema", "vigente"], busqueda=["nombre", "codigo"], campos=_cod,
))
registrar(Mantenedor(
    m.TipoMantenimiento, "tipos-mantenimiento", "Parametrización", "bi-wrench", orden=23,
    columnas=["nombre", "codigo", "es_sistema", "vigente"], busqueda=["nombre", "codigo"], campos=_cod + ["descripcion"],
))
registrar(Mantenedor(
    m.CondicionActivo, "condiciones", "Parametrización", "bi-clipboard-check", orden=24,
    columnas=["nombre", "codigo", "requiere_mantencion", "es_sistema", "vigente"], busqueda=["nombre", "codigo"],
    campos=_cod + ["requiere_mantencion"],
))
registrar(Mantenedor(
    m.TipoAlerta, "tipos-alerta", "Parametrización", "bi-bell", orden=25,
    columnas=["nombre", "codigo", "es_sistema", "vigente"], busqueda=["nombre", "codigo"], campos=_cod,
))
# Reglas de negocio: días de gracia, máximo de morosos, bloqueo automático Sí/No...
registrar(Mantenedor(
    m.ParametroSistema, "parametros-sistema", "Parametrización", "bi-sliders", orden=30,
    titulo="Reglas de negocio", columnas=["nombre", "clave", "valor", "es_sistema"],
    busqueda=["clave", "nombre"], campos=["clave", "nombre", "valor", "descripcion"],
    ayuda="Valores que controlan las reglas automáticas: días de gracia, bloqueo automático (Sí/No), avisos, etc.",
))
