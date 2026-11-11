"""
API REST (Django REST Framework).

Expone un endpoint CRUD por cada tabla y algunos endpoints de negocio.
Seguridad: sesión o Basic Auth + permisos de modelo de Django (view/add/change/delete).
"""
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from alertas.models import Alerta
from contratistas.models import Contratista, ResponsableObra
from inventario.models import Activo, Bodega, MovimientoActivo, Obra
from mantenimiento.models import Mantenimiento, PlanMantenimiento
from parametros import models as pm
from prestamos.models import DetallePrestamo, Prestamo


def crear_viewset(modelo, *, filtros=(), busqueda=(), solo_lectura=False, paginar=True, serializer=None, qs=None):
    if serializer is None:
        meta = type("Meta", (), {"model": modelo, "fields": "__all__"})
        serializer = type(f"{modelo.__name__}Serializer", (serializers.ModelSerializer,), {"Meta": meta})
    base = viewsets.ReadOnlyModelViewSet if solo_lectura else viewsets.ModelViewSet
    attrs = {
        "queryset": qs if qs is not None else modelo.objects.all(),
        "serializer_class": serializer,
        "filterset_fields": list(filtros),
        "search_fields": list(busqueda),
    }
    if not paginar:
        attrs["pagination_class"] = None
    return type(f"{modelo.__name__}ViewSet", (base,), attrs)


# ---------------- Serializers con datos legibles ----------------
class ActivoSerializer(serializers.ModelSerializer):
    estado_nombre = serializers.CharField(source="estado.nombre", read_only=True)
    bodega_nombre = serializers.CharField(source="bodega.nombre", read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    class Meta:
        model = Activo
        fields = "__all__"
        read_only_fields = ["estado"]  # el estado solo cambia por los flujos de negocio


class DetallePrestamoSerializer(serializers.ModelSerializer):
    activo_codigo = serializers.CharField(source="activo.codigo", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)

    class Meta:
        model = DetallePrestamo
        exclude = ["prestamo"]


class PrestamoSerializer(serializers.ModelSerializer):
    folio = serializers.CharField(read_only=True)
    contratista_nombre = serializers.CharField(source="contratista.razon_social", read_only=True)
    estado_nombre = serializers.CharField(source="estado.nombre", read_only=True)
    detalles = DetallePrestamoSerializer(many=True, read_only=True)
    dias_cobro = serializers.IntegerField(read_only=True)
    dias_atraso = serializers.IntegerField(read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)

    class Meta:
        model = Prestamo
        exclude = ["firma_entrega", "firma_devolucion"]


class ComunaSerializer(serializers.ModelSerializer):
    region = serializers.IntegerField(source="ciudad.region_id", read_only=True)

    class Meta:
        model = pm.Comuna
        fields = ["id", "nombre", "ciudad", "region", "vigente"]


VIEWSETS = {
    # Territorio (sin paginar: alimentan los selects encadenados Región -> Ciudad -> Comuna)
    "regiones": crear_viewset(pm.Region, filtros=["vigente"], busqueda=["nombre"], paginar=False),
    "ciudades": crear_viewset(pm.Ciudad, filtros=["region", "vigente"], busqueda=["nombre"], paginar=False),
    "comunas": crear_viewset(pm.Comuna, filtros=["ciudad", "ciudad__region", "vigente"], busqueda=["nombre"],
                             paginar=False, serializer=ComunaSerializer, qs=pm.Comuna.objects.select_related("ciudad")),
    # Parámetros
    "categorias": crear_viewset(pm.CategoriaActivo, filtros=["vigente"], busqueda=["nombre"], paginar=False),
    "marcas": crear_viewset(pm.Marca, filtros=["vigente"], busqueda=["nombre"], paginar=False),
    "cargos": crear_viewset(pm.Cargo, filtros=["vigente"], paginar=False),
    "estados-activo": crear_viewset(pm.EstadoActivo, paginar=False),
    "estados-prestamo": crear_viewset(pm.EstadoPrestamo, paginar=False),
    "estados-mantenimiento": crear_viewset(pm.EstadoMantenimiento, paginar=False),
    "tipos-mantenimiento": crear_viewset(pm.TipoMantenimiento, paginar=False),
    "tipos-alerta": crear_viewset(pm.TipoAlerta, paginar=False),
    "condiciones": crear_viewset(pm.CondicionActivo, paginar=False),
    "parametros-sistema": crear_viewset(pm.ParametroSistema, paginar=False),
    # Dominio
    "obras": crear_viewset(Obra, filtros=["vigente", "comuna"], busqueda=["codigo", "nombre"]),
    "bodegas": crear_viewset(Bodega, filtros=["vigente", "obra"], busqueda=["nombre"]),
    "activos": crear_viewset(Activo, filtros=["estado", "estado__codigo", "categoria", "bodega", "marca"],
                             busqueda=["codigo", "nombre", "numero_serie"], serializer=ActivoSerializer,
                             qs=Activo.objects.select_related("estado", "bodega", "categoria")),
    "movimientos": crear_viewset(MovimientoActivo, filtros=["activo"], solo_lectura=True),
    "contratistas": crear_viewset(Contratista, filtros=["bloqueado", "vigente"], busqueda=["rut", "razon_social"]),
    "responsables": crear_viewset(ResponsableObra, filtros=["contratista", "vigente"], busqueda=["nombre", "rut"],
                                  paginar=False),
    "prestamos": crear_viewset(Prestamo, filtros=["estado", "estado__codigo", "contratista", "obra"],
                               busqueda=["contratista__razon_social"], solo_lectura=True, serializer=PrestamoSerializer,
                               qs=Prestamo.objects.select_related("contratista", "estado").prefetch_related("detalles__activo")),
    "planes": crear_viewset(PlanMantenimiento, filtros=["activo", "vigente"]),
    "mantenimientos": crear_viewset(Mantenimiento, filtros=["activo", "estado", "tipo"], solo_lectura=True),
    "alertas": crear_viewset(Alerta, filtros=["resuelta", "tipo", "contratista"], solo_lectura=True),
}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resumen(request):
    """KPIs del dashboard (se refresca vía fetch cada 60 s)."""
    from django.db.models import Count

    estados = {e.codigo: e.total for e in pm.EstadoActivo.objects.annotate(total=Count("activos"))}
    abiertos = Prestamo.objects.filter(fecha_devolucion__isnull=True)
    return Response({
        "activos_por_estado": estados,
        "prestamos_abiertos": abiertos.count(),
        "prestamos_atrasados": sum(1 for p in abiertos if p.vencido),
        "contratistas_bloqueados": Contratista.objects.filter(bloqueado=True).count(),
        "alertas_pendientes": Alerta.objects.filter(resuelta=False).count(),
        "ots_abiertas": Mantenimiento.objects.filter(estado__codigo__in=["PROGRAMADA", "EN_PROCESO"]).count(),
    })
