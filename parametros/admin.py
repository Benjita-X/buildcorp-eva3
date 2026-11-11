from django.contrib import admin

from core.admin_utils import ParametroCodificadoAdmin

from . import models as m


class CiudadInline(admin.TabularInline):
    model = m.Ciudad
    extra = 0
    show_change_link = True


class ComunaInline(admin.TabularInline):
    model = m.Comuna
    extra = 0


@admin.register(m.Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "total_ciudades", "orden", "vigente"]
    list_editable = ["orden", "vigente"]
    search_fields = ["codigo", "nombre"]
    list_filter = ["vigente"]
    inlines = [CiudadInline]

    @admin.display(description="Ciudades")
    def total_ciudades(self, obj):
        return obj.ciudades.count()


@admin.register(m.Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "region", "total_comunas", "vigente"]
    list_filter = ["region", "vigente"]
    search_fields = ["nombre", "region__nombre"]
    autocomplete_fields = ["region"]
    inlines = [ComunaInline]

    @admin.display(description="Comunas")
    def total_comunas(self, obj):
        return obj.comunas.count()


@admin.register(m.Comuna)
class ComunaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "ciudad", "region_nombre", "vigente"]
    list_filter = ["ciudad__region", "vigente"]
    search_fields = ["nombre", "ciudad__nombre"]
    autocomplete_fields = ["ciudad"]
    list_select_related = ["ciudad__region"]

    @admin.display(description="Región", ordering="ciudad__region__nombre")
    def region_nombre(self, obj):
        return obj.ciudad.region


@admin.register(m.CategoriaActivo, m.Marca, m.Cargo)
class CatalogoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "vigente"]
    list_editable = ["vigente"]
    list_filter = ["vigente"]
    search_fields = ["nombre"]


@admin.register(m.EstadoActivo)
class EstadoActivoAdmin(ParametroCodificadoAdmin):
    list_display = ParametroCodificadoAdmin.list_display + ["permite_prestamo"]


@admin.register(m.CondicionActivo)
class CondicionAdmin(ParametroCodificadoAdmin):
    list_display = ParametroCodificadoAdmin.list_display + ["requiere_mantencion"]


admin.site.register([m.EstadoPrestamo, m.EstadoMantenimiento, m.TipoMantenimiento, m.TipoAlerta], ParametroCodificadoAdmin)


@admin.register(m.ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ["clave", "nombre", "valor", "es_sistema"]
    list_editable = ["valor"]
    search_fields = ["clave", "nombre"]
    readonly_fields = ["es_sistema"]

    def get_readonly_fields(self, request, obj=None):
        return ["es_sistema", "clave"] if obj and obj.es_sistema else ["es_sistema"]

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.es_sistema) and super().has_delete_permission(request, obj)
