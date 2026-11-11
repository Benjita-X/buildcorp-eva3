# Pantallas de administración (mantenedores con templates) de la app contratistas
from core.crud import Mantenedor, registrar

from .models import Contratista, ResponsableObra

# /m/contratistas/ (al abrir uno se ve su ficha propia)
registrar(Mantenedor(
    Contratista, "contratistas", "Contratistas", "bi-briefcase", orden=1,
    columnas=["rut", "razon_social", "comuna", "telefono", "bloqueado", "vigente"],
    busqueda=["rut", "razon_social", "nombre_fantasia", "email"], filtros=["bloqueado", "vigente"],
    url_detalle="contratistas:detalle",
))
# /m/responsables/
registrar(Mantenedor(
    ResponsableObra, "responsables", "Contratistas", "bi-person-vcard", orden=2,
    titulo="Responsables de obra",
    columnas=["nombre", "rut", "contratista", "cargo", "telefono", "vigente"],
    busqueda=["nombre", "rut", "contratista__razon_social"], filtros=["contratista", "cargo", "vigente"],
))
