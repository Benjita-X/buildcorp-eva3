from django.contrib import admin
from django.utils.html import format_html

from core.admin_utils import badge, badge_estado

from .models import DetallePrestamo, Prestamo


class DetalleInline(admin.TabularInline):
    model = DetallePrestamo
    extra = 0
    fields = ["activo", "bodega_origen", "tarifa_diaria", "horas_uso", "condicion", "devuelto"]
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ["folio", "contratista", "obra", "fecha_entrega", "fecha_compromiso", "estado_badge", "atraso", "total_fmt"]
    list_filter = ["estado", "obra", "contratista"]
    search_fields = ["contratista__razon_social", "contratista__rut", "responsable__nombre", "obra__codigo"]
    list_select_related = ["contratista", "obra", "estado"]
    date_hierarchy = "fecha_entrega"
    inlines = [DetalleInline]
    readonly_fields = ["firma_entrega_img", "firma_devolucion_img", "usuario_entrega", "usuario_recepcion",
                       "fecha_devolucion", "total_fmt"]
    fieldsets = [
        ("Entrega", {"fields": [("contratista", "responsable"), ("obra", "estado"),
                                ("fecha_entrega", "fecha_compromiso"), "observaciones", "usuario_entrega", "firma_entrega_img"]}),
        ("Devolución", {"fields": [("fecha_devolucion", "bodega_recepcion"), "devuelto_por", "observaciones_devolucion",
                                   "usuario_recepcion", "firma_devolucion_img"]}),
        ("Cobro", {"fields": ["total_fmt"]}),
    ]

    def has_add_permission(self, request):
        return False  # los préstamos se crean en el flujo con firma digital (/prestamos/nuevo/)

    @admin.display(description="Estado", ordering="estado__orden")
    def estado_badge(self, obj):
        return badge_estado(obj.estado)

    @admin.display(description="Atraso")
    def atraso(self, obj):
        return badge(f"{obj.dias_atraso} día(s)", "danger") if obj.dias_atraso else "—"

    @admin.display(description="Total cobro")
    def total_fmt(self, obj):
        return f"$ {obj.total:,.0f}".replace(",", ".")

    def _firma(self, data):
        return format_html('<img src="{}" style="max-height:120px;border:1px solid #ccc;background:#fff">', data) if data else "—"

    @admin.display(description="Firma de entrega")
    def firma_entrega_img(self, obj):
        return self._firma(obj.firma_entrega)

    @admin.display(description="Firma de devolución")
    def firma_devolucion_img(self, obj):
        return self._firma(obj.firma_devolucion)
