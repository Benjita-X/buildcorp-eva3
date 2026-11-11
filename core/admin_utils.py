# =============================================================================
# Ayudas para personalizar el Django Admin: etiquetas de colores para los
# estados y una configuración común para las tablas de estados y tipos.
# =============================================================================
from django.contrib import admin
from django.utils.html import format_html  # arma HTML de forma segura

# Colores de Bootstrap en formato hexadecimal
COLORES_HEX = {
    "primary": "#0d6efd", "secondary": "#6c757d", "success": "#198754", "danger": "#dc3545",
    "warning": "#ffc107", "info": "#0dcaf0", "dark": "#212529",
}


# Devuelve una etiqueta de color (badge) para mostrar en las listas del admin
def badge(texto, color="secondary"):
    fondo = COLORES_HEX.get(color, "#6c757d")
    texto_color = "#000" if color in ("warning", "info") else "#fff"  # texto negro en fondos claros
    return format_html(
        '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">{}</span>',
        fondo, texto_color, texto,
    )


# Etiqueta de color para un estado (usa el color guardado en la tabla de estados)
def badge_estado(obj_estado):
    if obj_estado is None:
        return "—"
    return badge(obj_estado.nombre, getattr(obj_estado, "color", "secondary"))


# Configuración del admin para las tablas de estados y tipos (EstadoActivo, TipoAlerta...)
class ParametroCodificadoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "color_badge", "orden", "es_sistema", "vigente"]  # columnas
    list_editable = ["orden", "vigente"]       # se pueden editar directo en la lista
    list_filter = ["vigente", "es_sistema"]    # filtros de la derecha
    search_fields = ["nombre", "codigo"]       # buscador
    readonly_fields = ["es_sistema"]           # campo que no se puede editar

    # Columna que muestra cómo se ve la etiqueta con su color
    @admin.display(description="Vista previa")
    def color_badge(self, obj):
        return badge(obj.nombre, obj.color)

    # Si el registro es de sistema, su código no se puede cambiar
    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.es_sistema:
            ro.append("codigo")
        return ro

    # Los registros de sistema no se pueden eliminar (los usa la lógica del sistema)
    def has_delete_permission(self, request, obj=None):
        if obj and obj.es_sistema:
            return False
        return super().has_delete_permission(request, obj)
