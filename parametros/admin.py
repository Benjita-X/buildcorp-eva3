# =============================================================================
# Django Admin de las tablas de parametrización.
#   list_display  = columnas de la lista
#   list_filter   = filtros de la derecha
#   search_fields = buscador
#   list_editable = campos que se editan directo en la lista
#   inlines       = tablas relacionadas que se muestran dentro del registro
# =============================================================================
from django.contrib import admin

from core.admin_utils import ParametroCodificadoAdmin

from . import models as m


# Muestra las ciudades dentro de la página de una región
class CiudadInline(admin.TabularInline):
    model = m.Ciudad
    extra = 0               # no agrega filas vacías
    show_change_link = True


# Muestra las comunas dentro de la página de una ciudad
class ComunaInline(admin.TabularInline):
    model = m.Comuna
    extra = 0


# @admin.register(Modelo) registra la tabla en el Django Admin
@admin.register(m.Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "total_ciudades", "orden", "vigente"]
    list_editable = ["orden", "vigente"]
    search_fields = ["codigo", "nombre"]
    list_filter = ["vigente"]
    inlines = [CiudadInline]

    # Columna calculada: cuántas ciudades tiene la región
    @admin.display(description="Ciudades")
    def total_ciudades(self, obj):
        return obj.ciudades.count()


@admin.register(m.Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "region", "total_comunas", "vigente"]
    list_filter = ["region", "vigente"]
    search_fields = ["nombre", "region__nombre"]
    autocomplete_fields = ["region"]  # selector con buscador
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
    list_select_related = ["ciudad__region"]  # trae la región en la misma consulta

    @admin.display(description="Región", ordering="ciudad__region__nombre")
    def region_nombre(self, obj):
        return obj.ciudad.region


# La misma configuración sirve para categorías, marcas y cargos
@admin.register(m.CategoriaActivo, m.Marca, m.Cargo)
class CatalogoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "vigente"]
    list_editable = ["vigente"]
    list_filter = ["vigente"]
    search_fields = ["nombre"]


# Estados de activo (usa la configuración común de estados y tipos)
@admin.register(m.EstadoActivo)
class EstadoActivoAdmin(ParametroCodificadoAdmin):
    list_display = ParametroCodificadoAdmin.list_display + ["permite_prestamo"]


@admin.register(m.CondicionActivo)
class CondicionAdmin(ParametroCodificadoAdmin):
    list_display = ParametroCodificadoAdmin.list_display + ["requiere_mantencion"]


# Registra varios modelos con la misma configuración
admin.site.register([m.EstadoPrestamo, m.EstadoMantenimiento, m.TipoMantenimiento, m.TipoAlerta], ParametroCodificadoAdmin)


# Reglas de negocio
@admin.register(m.ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ["clave", "nombre", "valor", "es_sistema"]
    list_editable = ["valor"]  # el valor se cambia directo en la lista
    search_fields = ["clave", "nombre"]
    readonly_fields = ["es_sistema"]

    # La clave de un parámetro de sistema no se puede cambiar
    def get_readonly_fields(self, request, obj=None):
        return ["es_sistema", "clave"] if obj and obj.es_sistema else ["es_sistema"]

    # Un parámetro de sistema no se puede eliminar
    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.es_sistema) and super().has_delete_permission(request, obj)
