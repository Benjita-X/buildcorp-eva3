# Django Admin de alertas (con acción masiva para marcarlas como resueltas)
from django.contrib import admin

from core.admin_utils import badge_estado

from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ["fecha", "tipo_badge", "mensaje", "contratista", "resuelta"]
    list_filter = ["resuelta", "tipo"]
    search_fields = ["mensaje", "contratista__razon_social"]
    date_hierarchy = "fecha"
    readonly_fields = ["fecha", "fecha_resolucion", "resuelta_por"]
    actions = ["marcar_resueltas"]

    @admin.display(description="Tipo", ordering="tipo__orden")
    def tipo_badge(self, obj):
        return badge_estado(obj.tipo)

    @admin.action(description="Marcar como resueltas")
    def marcar_resueltas(self, request, queryset):
        for a in queryset.filter(resuelta=False):
            a.resolver(request.user)
        self.message_user(request, "Alertas marcadas como resueltas.")
