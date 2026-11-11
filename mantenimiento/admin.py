from django.contrib import admin

from core.admin_utils import badge, badge_estado

from .models import Mantenimiento, PlanMantenimiento


@admin.register(PlanMantenimiento)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["activo", "descripcion", "tipo", "cada_horas", "cada_dias", "proxima_fecha", "situacion", "vigente"]
    list_filter = ["tipo", "vigente"]
    search_fields = ["activo__codigo", "activo__nombre", "descripcion"]
    autocomplete_fields = ["activo"]
    list_select_related = ["activo", "tipo"]

    @admin.display(description="Situación")
    def situacion(self, obj):
        if obj.esta_vencido:
            return badge("Vencido", "danger")
        if obj.por_vencer:
            return badge("Por vencer", "warning")
        return badge(f"{obj.porcentaje_uso}% usado", "success")


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ["folio", "activo", "tipo", "estado_badge", "fecha_programada", "tecnico", "costo"]
    list_filter = ["estado", "tipo"]
    search_fields = ["activo__codigo", "activo__nombre", "tecnico", "descripcion"]
    autocomplete_fields = ["activo"]
    date_hierarchy = "fecha_programada"
    readonly_fields = ["fecha_inicio", "fecha_termino", "horas_activo", "creado_por", "creado"]
    list_select_related = ["activo", "tipo", "estado"]

    @admin.display(description="Estado", ordering="estado__orden")
    def estado_badge(self, obj):
        return badge_estado(obj.estado)
