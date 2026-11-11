from django.contrib import admin
from django.utils.html import format_html

COLORES_HEX = {
    "primary": "#0d6efd", "secondary": "#6c757d", "success": "#198754", "danger": "#dc3545",
    "warning": "#ffc107", "info": "#0dcaf0", "dark": "#212529",
}


def badge(texto, color="secondary"):
    fondo = COLORES_HEX.get(color, "#6c757d")
    texto_color = "#000" if color in ("warning", "info") else "#fff"
    return format_html(
        '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">{}</span>',
        fondo, texto_color, texto,
    )


def badge_estado(obj_estado):
    if obj_estado is None:
        return "—"
    return badge(obj_estado.nombre, getattr(obj_estado, "color", "secondary"))


class ParametroCodificadoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "color_badge", "orden", "es_sistema", "vigente"]
    list_editable = ["orden", "vigente"]
    list_filter = ["vigente", "es_sistema"]
    search_fields = ["nombre", "codigo"]
    readonly_fields = ["es_sistema"]

    @admin.display(description="Vista previa")
    def color_badge(self, obj):
        return badge(obj.nombre, obj.color)

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.es_sistema:
            ro.append("codigo")
        return ro

    def has_delete_permission(self, request, obj=None):
        if obj and obj.es_sistema:
            return False
        return super().has_delete_permission(request, obj)
