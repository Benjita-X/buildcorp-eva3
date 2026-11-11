# =============================================================================
# Django Admin del inventario (obras, bodegas, activos y movimientos).
#   list_display  = columnas de la lista        list_filter   = filtros de la derecha
#   search_fields = buscador                    inlines       = tablas relacionadas dentro del registro
#   fieldsets     = ordena el formulario en secciones
# =============================================================================
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from core.admin_utils import badge_estado
from mantenimiento.models import PlanMantenimiento

from .models import Activo, Bodega, MovimientoActivo, Obra


# Muestra las bodegas dentro de la página de una obra
class BodegaInline(admin.TabularInline):
    model = Bodega
    extra = 0
    fields = ["nombre", "direccion", "comuna", "encargado", "vigente"]


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "comuna", "jefe_obra", "fecha_inicio", "fecha_termino", "vigente"]
    list_filter = ["vigente", "comuna__ciudad__region"]  # filtro por región (a través de la comuna)
    search_fields = ["codigo", "nombre", "jefe_obra"]
    autocomplete_fields = ["comuna"]
    date_hierarchy = "fecha_inicio"  # navegación por fechas arriba de la lista
    inlines = [BodegaInline]


@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "obra", "comuna", "encargado", "total_activos", "vigente"]
    list_filter = ["vigente", "obra"]
    search_fields = ["nombre", "direccion"]
    autocomplete_fields = ["comuna"]

    # Columna calculada: "Central" u "Obra"
    @admin.display(description="Tipo")
    def tipo(self, obj):
        return "Central" if obj.es_central else "Obra"

    # Columna calculada: cuántas herramientas hay en la bodega
    @admin.display(description="Activos")
    def total_activos(self, obj):
        return obj.activos.count()


# Muestra la trazabilidad dentro del activo (solo lectura: no se puede agregar ni borrar)
class MovimientoInline(admin.TabularInline):
    model = MovimientoActivo
    extra = 0
    can_delete = False
    fields = ["fecha", "estado_anterior", "estado_nuevo", "bodega_origen", "bodega_destino", "usuario", "descripcion"]
    readonly_fields = fields
    ordering = ["-fecha"]

    def has_add_permission(self, request, obj=None):
        return False


# Muestra los planes de mantención dentro del activo
class PlanInline(admin.TabularInline):
    model = PlanMantenimiento
    extra = 0
    fields = ["tipo", "descripcion", "cada_horas", "cada_dias", "ultima_fecha", "ultimas_horas", "vigente"]


@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "categoria", "marca", "estado_badge", "bodega", "horas_uso", "tarifa_fmt", "hoja_vida"]
    list_filter = ["estado", "categoria", "marca", "bodega"]
    search_fields = ["codigo", "nombre", "numero_serie", "modelo"]
    list_select_related = ["estado", "categoria", "marca", "bodega"]  # trae las relaciones en una consulta
    list_per_page = 25
    readonly_fields = ["creado", "actualizado"]
    # El formulario del activo ordenado en secciones
    fieldsets = [
        ("Identificación", {"fields": [("codigo", "nombre"), ("categoria", "marca"), ("modelo", "numero_serie")]}),
        ("Ubicación y estado", {"fields": [("estado", "bodega"), "horas_uso"]}),
        ("Valores", {"fields": [("tarifa_diaria", "valor_compra"), "fecha_adquisicion"]}),
        ("Otros", {"fields": ["observaciones", ("creado", "actualizado")], "classes": ["collapse"]}),
    ]
    inlines = [PlanInline, MovimientoInline]

    # Estado con etiqueta de color
    @admin.display(description="Estado", ordering="estado__orden")
    def estado_badge(self, obj):
        return badge_estado(obj.estado)

    # Tarifa con formato de pesos
    @admin.display(description="Tarifa diaria", ordering="tarifa_diaria")
    def tarifa_fmt(self, obj):
        return f"$ {obj.tarifa_diaria:,.0f}".replace(",", ".")

    # Enlace a la hoja de vida del activo (pantalla propia del sistema)
    @admin.display(description="")
    def hoja_vida(self, obj):
        return format_html('<a href="{}" target="_blank">Hoja de vida ↗</a>', reverse("inventario:activo_detalle", args=[obj.pk]))

    # Al guardar desde el admin también queda registrado en la trazabilidad quién lo hizo
    def save_model(self, request, obj, form, change):
        obj._usuario, obj._motivo = request.user, "Modificación desde Django Admin"
        super().save_model(request, obj, form, change)


# Movimientos: solo se pueden ver (no agregar ni modificar), para que el historial sea confiable
@admin.register(MovimientoActivo)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ["fecha", "activo", "estado_anterior", "estado_nuevo", "bodega_origen", "bodega_destino", "usuario"]
    list_filter = ["estado_nuevo", "bodega_destino"]
    search_fields = ["activo__codigo", "descripcion"]
    date_hierarchy = "fecha"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
